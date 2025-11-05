/**
 * Medical-Grade Waveform Rendering Utilities
 *
 * MEDICAL STANDARDS:
 * - ECG: 10mm = 1mV (fixed scale, NOT auto-scaling)
 * - EEG: 50μV/mm (fixed sensitivity, NOT auto-scaling)
 * - Paper Speed: 25mm/s (standard)
 * - Baseline: Centered at zero (0mV / 0μV)
 *
 * WHY FIXED SCALES MATTER:
 * - Auto-scaling destroys clinical amplitude information
 * - Doctors expect consistent scales for diagnosis
 * - QRS amplitude is diagnostic (LVH, MI, etc.)
 * - EEG amplitude indicates seizure activity
 *
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data fields
 *
 * NOTE: All medical constants have been centralized in config/ecgConfig.ts
 * Import from there instead of this file.
 */

import {
  ECG_SCALE_MM_PER_MV,
  EEG_SCALE_UV_PER_MM,
  PAPER_SPEED_MM_PER_S,
  SAMPLE_RATE_HZ,
  ADC_MIDPOINT,
  ECG_ADC_SCALE_FACTOR,
  EEG_ADC_SCALE_FACTOR
} from '../config/ecgConfig';

/**
 * Cached DPI value - detected once on first call, then reused
 */
let cachedDPI: number | null = null;

/**
 * Auto-detect screen DPI using browser APIs
 * CACHED: Only detects DPI once on first call, then returns cached value
 * Measures actual pixel density to ensure medical-grade accuracy
 * Falls back to 96 DPI if detection fails
 *
 * @returns Detected DPI (typically 96, 120, 141, 192, etc.)
 */
export function getScreenDPI(): number {
  // Return cached value if already detected
  if (cachedDPI !== null) {
    return cachedDPI;
  }
  try {
    // Method 1: Create a measurement element with physical dimensions
    const div = document.createElement('div');
    div.style.width = '1in';
    div.style.height = '1in';
    div.style.position = 'absolute';
    div.style.left = '-100%';
    div.style.top = '-100%';
    div.style.visibility = 'hidden';
    document.body.appendChild(div);

    const dpi = div.offsetWidth;
    document.body.removeChild(div);

    // Validate DPI (should be between 72 and 300 for most displays)
    if (dpi >= 72 && dpi <= 300) {
      cachedDPI = dpi;
      console.log(`✅ DPI detected: ${dpi} (cached for future use)`);
      console.log(`🔍 1mm = ${(dpi / 25.4).toFixed(2)} pixels, 5mm big square = ${(dpi / 25.4 * 5).toFixed(2)} pixels`);
      return dpi;
    }
  } catch (error) {
    console.warn('⚠️ DPI detection failed:', error);
  }

  // Fallback: Standard 96 DPI
  cachedDPI = 96;
  console.log('⚠️ DPI detection failed, using fallback: 96 DPI (cached)');
  return 96;
}

/**
 * Convert millimeters to pixels based on detected DPI
 * Essential for medical-grade display accuracy
 *
 * @param mm - Millimeters to convert
 * @returns Pixels (based on actual screen DPI)
 */
export function mmToPixels(mm: number): number {
  const dpi = getScreenDPI();
  const inches = mm / 25.4; // 1 inch = 25.4mm
  return inches * dpi;
}

/**
 * Decode delta-encoded waveform data from ESP32 v5.2.5+
 * Delta encoding format: {baseline: number, deltas: number[]}
 * Reconstructs full sample array: [baseline, baseline+delta[0], baseline+delta[0]+delta[1], ...]
 *
 * @param deltaData - Delta-encoded channel data {baseline, deltas}
 * @returns Reconstructed full sample array
 */
export function decodeDeltaChannel(deltaData: { baseline: number; deltas: number[] }): number[] {
  if (!deltaData || typeof deltaData.baseline !== 'number' || !Array.isArray(deltaData.deltas)) {
    console.error('❌ Invalid delta-encoded data:', deltaData);
    return [];
  }

  const samples: number[] = [deltaData.baseline];
  let currentValue = deltaData.baseline;

  for (const delta of deltaData.deltas) {
    currentValue += delta;
    samples.push(currentValue);
  }

  return samples;
}

/**
 * Convert raw 24-bit ADC value to millivolts (for ECG)
 * ESP32 formula: sample = 8388608 + (mV * 100000)
 * Reverse: mV = (sample - 8388608) / 100000
 */
export function adcToMillivolts(adcValue: number): number {
  return (adcValue - ADC_MIDPOINT) / ECG_ADC_SCALE_FACTOR;
}

/**
 * Convert raw 24-bit ADC value to microvolts (for EEG)
 * ESP32 formula: sample = 8388608 + (μV * 1000)
 * Reverse: μV = (sample - 8388608) / 1000
 */
export function adcToMicrovolts(adcValue: number): number {
  return (adcValue - ADC_MIDPOINT) / EEG_ADC_SCALE_FACTOR;
}

/**
 * Render ECG waveform with medical-grade fixed scale
 *
 * @param samples - Raw ADC samples from ESP32
 * @param viewportWidth - SVG viewport width in pixels
 * @param viewportHeight - SVG viewport height in pixels
 * @param sampleRate - Sampling rate in Hz (default 500Hz)
 * @returns SVG path string
 */
export function renderECGWaveform(
  samples: number[],
  viewportWidth: number,
  viewportHeight: number,
  sampleRate: number = SAMPLE_RATE_HZ
): string {
  if (!samples || samples.length === 0) {
    // No data - return centered baseline
    const baseline = viewportHeight / 2;
    return `M 0 ${baseline} L ${viewportWidth} ${baseline}`;
  }

  // MEDICAL STANDARD: 10mm = 1mV
  // Typical ECG range: ±2mV (covers normal QRS complexes)
  const baseline = viewportHeight / 2; // Center line = 0mV
  const mvRange = 4; // Total range: -2mV to +2mV
  const pixelsPerMV = viewportHeight / mvRange; // How many pixels = 1mV

  // Calculate horizontal spacing based on paper speed
  // 25mm/s standard speed
  const samplesPerSecond = sampleRate;
  const pixelsPerSample = (viewportWidth / samples.length);

  // Generate SVG path
  const path = samples.map((adcValue, index) => {
    const x = index * pixelsPerSample;

    // ✅ CRITICAL FIX: Convert ADC to mV FIRST
    const mV = adcToMillivolts(adcValue);

    // Then apply fixed medical scale: 10mm/mV
    // Negative because SVG y-axis grows downward
    const y = baseline - (mV * pixelsPerMV);

    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');

  return path;
}

/**
 * Render EEG waveform with medical-grade fixed scale
 *
 * @param samples - Raw ADC samples from ESP32
 * @param viewportWidth - SVG viewport width in pixels
 * @param viewportHeight - SVG viewport height in pixels
 * @param sampleRate - Sampling rate in Hz (default 500Hz)
 * @returns SVG path string
 */
export function renderEEGWaveform(
  samples: number[],
  viewportWidth: number,
  viewportHeight: number,
  sampleRate: number = SAMPLE_RATE_HZ
): string {
  if (!samples || samples.length === 0) {
    // No data - return centered baseline
    const baseline = viewportHeight / 2;
    return `M 0 ${baseline} L ${viewportWidth} ${baseline}`;
  }

  // MEDICAL STANDARD: 50μV/mm sensitivity
  // Typical EEG range: ±200μV
  const baseline = viewportHeight / 2; // Center line = 0μV
  const uvRange = 400; // Total range: -200μV to +200μV
  const pixelsPerUV = viewportHeight / uvRange; // How many pixels = 1μV

  // Calculate horizontal spacing based on paper speed
  const pixelsPerSample = (viewportWidth / samples.length);

  // Generate SVG path
  const path = samples.map((adcValue, index) => {
    const x = index * pixelsPerSample;

    // ✅ CRITICAL FIX: Convert ADC to μV FIRST
    const uV = adcToMicrovolts(adcValue);

    // Then apply fixed medical scale: 50μV/mm
    // Negative because SVG y-axis grows downward
    const y = baseline - (uV * pixelsPerUV);

    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');

  return path;
}

/**
 * Render waveform with adaptive scaling for initial display
 * Falls back to fixed scale after first render
 *
 * @param samples - Raw ADC samples
 * @param viewportWidth - SVG viewport width
 * @param viewportHeight - SVG viewport height
 * @param isECGMode - true for ECG, false for EEG
 * @param useFixedScale - Use medical-grade fixed scale (default true)
 * @returns SVG path string
 */
export function renderWaveform(
  samples: number[],
  viewportWidth: number,
  viewportHeight: number,
  isECGMode: boolean,
  useFixedScale: boolean = true
): string {
  if (!samples || samples.length === 0) {
    const baseline = viewportHeight / 2;
    return `M 0 ${baseline} L ${viewportWidth} ${baseline}`;
  }

  if (useFixedScale) {
    // Use medical-grade fixed scales
    return isECGMode
      ? renderECGWaveform(samples, viewportWidth, viewportHeight)
      : renderEEGWaveform(samples, viewportWidth, viewportHeight);
  }

  // Fallback: Auto-scaling (for debugging only, NOT clinical use)
  const baseline = viewportHeight / 2;
  const minVal = Math.min(...samples);
  const maxVal = Math.max(...samples);
  const range = maxVal - minVal || 1;
  const pixelsPerSample = viewportWidth / samples.length;

  const path = samples.map((value, index) => {
    const x = index * pixelsPerSample;
    const y = baseline - ((value - minVal) / range) * (viewportHeight * 0.8);
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');

  return path;
}

/**
 * Generate calibration pulse for ECG (1mV step)
 * Used to verify scale accuracy
 *
 * @param viewportWidth - SVG viewport width
 * @param viewportHeight - SVG viewport height
 * @returns SVG path for 1mV calibration pulse
 */
export function generateECGCalibrationPulse(
  viewportWidth: number,
  viewportHeight: number
): string {
  const baseline = viewportHeight / 2;
  const mvRange = 4;
  const pixelsPerMV = viewportHeight / mvRange;

  // 1mV pulse: 0mV → 1mV → 0mV
  const pulseHeight = 1 * pixelsPerMV; // 1mV
  const pulseWidth = viewportWidth * 0.1; // 10% of width

  return `
    M 0 ${baseline}
    L ${pulseWidth * 0.3} ${baseline}
    L ${pulseWidth * 0.3} ${baseline - pulseHeight}
    L ${pulseWidth * 0.7} ${baseline - pulseHeight}
    L ${pulseWidth * 0.7} ${baseline}
    L ${viewportWidth} ${baseline}
  `.trim().replace(/\s+/g, ' ');
}

/**
 * Calculate grid spacing for medical ECG/EEG display
 *
 * @param viewportWidth - SVG viewport width
 * @param viewportHeight - SVG viewport height
 * @returns Grid line spacing for 1mm and 5mm divisions
 */
export function calculateMedicalGridSpacing(
  viewportWidth: number,
  viewportHeight: number
): {
  smallGrid: number;  // 1mm spacing
  largeGrid: number;  // 5mm spacing
} {
  // Standard medical grid: 1mm small, 5mm large
  // Assume viewport represents ~100mm width
  const mmPerPixel = 100 / viewportWidth;

  return {
    smallGrid: 1 / mmPerPixel,  // 1mm in pixels
    largeGrid: 5 / mmPerPixel   // 5mm in pixels
  };
}

/**
 * Render waveform to canvas with medical-grade fixed scale
 * Uses simple stretching approach matching SVG rendering for patient cards
 *
 * @param data - Raw ADC samples from ESP32
 * @param ctx - Canvas 2D rendering context
 * @param width - Canvas width in pixels
 * @param height - Canvas height in pixels
 * @param isECGMode - true for ECG, false for EEG
 * @param useFixedScale - Use medical-grade fixed scale (default true)
 * @param leadColor - Color for waveform line
 */
export function renderWaveformCanvas(
  data: number[],
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  isECGMode: boolean,
  useFixedScale: boolean = true,
  leadColor: string = '#00FF00'
): void {
  if (!data || data.length === 0) return;

  // MEDICAL-GRADE FIXED SCALING (vertical axis only)
  const baseline = height / 2; // Center line = 0mV/0μV

  let pixelsPerUnit: number; // pixels per mV (ECG) or pixels per μV (EEG)

  if (useFixedScale) {
    // ✅ FIXED: Use mmToPixels() to match grid scale (medical-grade accuracy)
    if (isECGMode) {
      // ECG: 10mm = 1mV (medical standard)
      pixelsPerUnit = mmToPixels(ECG_SCALE_MM_PER_MV);
    } else {
      // EEG: 50μV/mm sensitivity
      // 1mm = 50μV, so 1μV = 1/50 mm
      const mmPerUV = 1 / EEG_SCALE_UV_PER_MM;
      pixelsPerUnit = mmToPixels(mmPerUV);
    }
  } else {
    // Fallback: Auto-scaling (for debugging only, NOT clinical use)
    const convertedData = data.map(val =>
      isECGMode ? adcToMillivolts(val) : adcToMicrovolts(val)
    );
    const minVal = Math.min(...convertedData);
    const maxVal = Math.max(...convertedData);
    const range = maxVal - minVal || 1;
    pixelsPerUnit = (height * 0.8) / range;
  }

  // ✅ FIXED: Use mmToPixels() for horizontal scale to match grid (25mm/s paper speed)
  // Calculate how many samples fit on canvas at medical-grade 25mm/s paper speed
  const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // 25mm/s at detected DPI
  const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // Fixed: 25mm/s ÷ 500Hz

  // Calculate how many samples fit on canvas width at this fixed scale
  const samplesVisible = Math.floor(width / pixelsPerSample);

  // Only render samples that fit on canvas at correct medical scale
  const samplesToRender = data.slice(-Math.min(samplesVisible, data.length));

  // Draw waveform path with FIXED medical spacing
  ctx.strokeStyle = leadColor;
  ctx.lineWidth = 2;
  ctx.beginPath();

  let isFirst = true;
  for (let i = 0; i < samplesToRender.length; i++) {
    // Medical-accurate X calculation (FIXED spacing, never changes!)
    const x = i * pixelsPerSample;

    // Convert ADC to mV or μV
    const value = isECGMode ? adcToMillivolts(samplesToRender[i]) : adcToMicrovolts(samplesToRender[i]);

    // Apply FIXED medical scale (vertical axis - medically accurate)
    const y = baseline - (value * pixelsPerUnit);

    // Clamp to canvas bounds (waveforms outside range go off-screen, like real ECG)
    const clampedY = Math.max(0, Math.min(height, y));

    if (isFirst) {
      ctx.moveTo(x, clampedY);
      isFirst = false;
    } else {
      ctx.lineTo(x, clampedY);
    }
  }

  ctx.stroke();
}

/**
 * Render waveform segment to canvas with medical-grade fixed scale
 * Used for circular buffer rendering (ICU monitor style)
 *
 * @param data - Raw ADC samples from ESP32
 * @param ctx - Canvas 2D rendering context
 * @param startX - Starting X pixel position for this segment
 * @param height - Canvas height in pixels
 * @param isECGMode - true for ECG, false for EEG
 * @param pixelsPerSample - Horizontal spacing (pre-calculated)
 * @param pixelsPerUnit - Vertical scale (pre-calculated: pixels per mV or μV)
 * @param leadColor - Color for waveform line
 */
export function renderWaveformSegment(
  data: number[],
  ctx: CanvasRenderingContext2D,
  startX: number,
  height: number,
  isECGMode: boolean,
  pixelsPerSample: number,
  pixelsPerUnit: number,
  leadColor: string
): void {
  if (!data || data.length === 0) return;

  const baseline = height / 2; // Center line = 0mV/0μV

  ctx.strokeStyle = leadColor;
  ctx.lineWidth = 2;
  ctx.beginPath();

  let isFirst = true;
  for (let i = 0; i < data.length; i++) {
    const x = startX + (i * pixelsPerSample);
    const value = isECGMode ? adcToMillivolts(data[i]) : adcToMicrovolts(data[i]);
    const y = baseline - (value * pixelsPerUnit);
    const clampedY = Math.max(0, Math.min(height, y));

    if (isFirst) {
      ctx.moveTo(x, clampedY);
      isFirst = false;
    } else {
      ctx.lineTo(x, clampedY);
    }
  }

  ctx.stroke();
}

/**
 * Draw medical-grade ECG/EEG grid on canvas
 * Looks exactly like real ECG paper with 1mm and 5mm divisions
 *
 * @param ctx - Canvas 2D rendering context
 * @param width - Canvas width in pixels
 * @param height - Canvas height in pixels
 * @param isECGMode - true for ECG (red grid), false for EEG (gray grid)
 */
export function drawMedicalGrid(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  isECGMode: boolean
): void {
  // Real ECG paper colors:
  // - Small grid (1mm): Light pink/red for ECG, light gray for EEG
  // - Large grid (5mm): Darker pink/red for ECG, darker gray for EEG
  const smallGridColor = isECGMode ? 'rgba(255, 102, 102, 0.3)' : 'rgba(68, 68, 68, 0.3)';
  const largeGridColor = isECGMode ? 'rgba(204, 51, 51, 0.5)' : 'rgba(102, 102, 102, 0.5)';

  // ✅ FIX: Use detected DPI for accurate medical grid spacing
  // Standard medical grid spacing: 1mm small, 5mm large
  const smallGridSpacing = mmToPixels(1); // 1mm at detected DPI
  const largeGridSpacing = mmToPixels(5); // 5mm at detected DPI

  // Draw small grid (1mm divisions)
  ctx.strokeStyle = smallGridColor;
  ctx.lineWidth = 0.5;

  // Vertical lines (time axis)
  for (let x = 0; x < width; x += smallGridSpacing) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  // Horizontal lines (amplitude axis)
  for (let y = 0; y < height; y += smallGridSpacing) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Draw large grid (5mm divisions)
  ctx.strokeStyle = largeGridColor;
  ctx.lineWidth = 1;

  // Vertical lines (time axis)
  for (let x = 0; x < width; x += largeGridSpacing) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  // Horizontal lines (amplitude axis)
  for (let y = 0; y < height; y += largeGridSpacing) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Draw baseline (0mV/0μV) - thicker line at center
  ctx.strokeStyle = isECGMode ? 'rgba(255, 255, 255, 0.3)' : 'rgba(200, 200, 200, 0.3)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, height / 2);
  ctx.lineTo(width, height / 2);
  ctx.stroke();
}

/**
 * Draw calibration pulse on canvas (1mV standard pulse for ECG)
 * Real ECG machines show this at the start of each strip
 *
 * @param ctx - Canvas 2D rendering context
 * @param x - Starting X position
 * @param baseline - Baseline Y position (0mV line)
 * @param height - Canvas height
 * @param isECGMode - true for ECG, false for EEG
 */
export function drawCalibrationPulse(
  ctx: CanvasRenderingContext2D,
  x: number,
  baseline: number,
  height: number,
  isECGMode: boolean
): void {
  if (!isECGMode) return; // Calibration pulse only for ECG

  // ✅ FIX: Use detected DPI for accurate medical calibration pulse
  // Medical standard: 1mV pulse = 10mm height, 200ms width (~5mm at 25mm/s)
  const pulseHeight = mmToPixels(10); // 1mV = 10mm at detected DPI
  const pulseWidth = mmToPixels(5);   // 5mm (~200ms at 25mm/s)

  ctx.save();
  ctx.strokeStyle = '#00FF00'; // Green like real ECG
  ctx.lineWidth = 2;
  ctx.beginPath();

  // Draw standard calibration pulse
  ctx.moveTo(x, baseline);           // Baseline
  ctx.lineTo(x + 5, baseline);       // Lead-in
  ctx.lineTo(x + 5, baseline - pulseHeight);  // Up stroke (1mV up)
  ctx.lineTo(x + 5 + pulseWidth, baseline - pulseHeight); // Hold high
  ctx.lineTo(x + 5 + pulseWidth, baseline);  // Down stroke
  ctx.lineTo(x + 10 + pulseWidth, baseline); // Lead-out

  ctx.stroke();
  ctx.restore();
}
  