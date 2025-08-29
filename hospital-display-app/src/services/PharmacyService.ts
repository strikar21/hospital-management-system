// Pharmacy Integration Service - Handles medication dispensing and inventory
import { PharmacyOrder, Medication } from '../types';

export class PharmacyService {
  // Mock pharmacy orders database
  private static mockPharmacyOrders: PharmacyOrder[] = [
    {
      id: 'rx001',
      patientId: 'P001',
      medicationId: 'med001',
      prescriptionId: 'presc001',
      status: 'dispensed',
      quantity: 30,
      dispensedQuantity: 30,
      pharmacist: 'PharmD Johnson',
      performedBy: 'PharmD Johnson',
      completedAt: '2024-08-27T10:30:00Z',
      notes: 'Patient counseled on side effects and proper administration'
    },
    {
      id: 'rx002',
      patientId: 'P001',
      medicationId: 'med002',
      prescriptionId: 'presc002',
      status: 'verified',
      quantity: 60,
      pharmacist: 'PharmD Chen',
      performedBy: 'PharmD Chen',
      notes: 'Dosage verified against patient weight and renal function'
    },
    {
      id: 'rx003',
      patientId: 'P001',
      medicationId: 'med003',
      prescriptionId: 'presc003',
      status: 'pending',
      quantity: 90,
      notes: 'Awaiting insurance authorization'
    }
  ];

  // Mock drug inventory
  private static drugInventory = {
    'metformin': { 
      stock: 450, 
      minLevel: 100, 
      cost: 0.25, 
      supplier: 'Generic Pharma',
      lot: 'MET240827',
      expiry: '2025-08-27',
      location: 'A-15-B'
    },
    'lisinopril': { 
      stock: 280, 
      minLevel: 150, 
      cost: 0.15, 
      supplier: 'Cardinal Health',
      lot: 'LIS240825',
      expiry: '2025-12-15',
      location: 'B-22-A'
    },
    'warfarin': { 
      stock: 35, 
      minLevel: 50, 
      cost: 0.85, 
      supplier: 'Coumadin Corp',
      lot: 'WAR240801',
      expiry: '2025-05-10',
      location: 'C-05-C'
    },
    'aspirin': { 
      stock: 750, 
      minLevel: 200, 
      cost: 0.05, 
      supplier: 'Bayer',
      lot: 'ASP240820',
      expiry: '2026-02-20',
      location: 'A-03-A'
    },
    'insulin': { 
      stock: 25, 
      minLevel: 30, 
      cost: 15.50, 
      supplier: 'Novo Nordisk',
      lot: 'INS240826',
      expiry: '2024-12-26',
      location: 'FRIDGE-A1'
    }
  };

  // Get pharmacy orders for a patient
  static async getPatientPharmacyOrders(patientId: string): Promise<PharmacyOrder[]> {
    await new Promise(resolve => setTimeout(resolve, 600));
    return this.mockPharmacyOrders.filter(order => order.patientId === patientId);
  }

  // Create pharmacy order from medication
  static async createPharmacyOrder(medication: Medication, patientId: string): Promise<PharmacyOrder> {
    await new Promise(resolve => setTimeout(resolve, 800));
    
    const newOrder: PharmacyOrder = {
      id: `rx${Date.now()}`,
      patientId: patientId,
      medicationId: medication.id,
      prescriptionId: `presc${Date.now()}`,
      status: 'pending',
      quantity: this.parseQuantityFromDosage(medication.dosage, medication.frequency),
      notes: `Prescription for ${medication.name} - ${medication.dosage}, ${medication.frequency}`
    };

    this.mockPharmacyOrders.push(newOrder);
    return newOrder;
  }

  // Update pharmacy order status
  static async updateOrderStatus(
    orderId: string, 
    status: PharmacyOrder['status'],
    pharmacistId: string,
    notes?: string
  ): Promise<PharmacyOrder> {
    await new Promise(resolve => setTimeout(resolve, 400));
    
    const order = this.mockPharmacyOrders.find(o => o.id === orderId);
    if (!order) throw new Error('Order not found');

    order.status = status;
    order.pharmacist = pharmacistId;
    
    if (status === 'verified') {
      order.performedBy = pharmacistId;
    } else if (status === 'dispensed') {
      order.completedAt = new Date().toISOString();
      order.dispensedQuantity = order.quantity;
    }
    
    if (notes) {
      order.notes = notes;
    }

    return order;
  }

  // Check drug inventory
  static async checkDrugInventory(drugName: string): Promise<any> {
    await new Promise(resolve => setTimeout(resolve, 300));
    
    const drug = drugName.toLowerCase();
    return this.drugInventory[drug as keyof typeof this.drugInventory] || null;
  }

  // Get low stock medications
  static async getLowStockMedications(): Promise<Array<{drug: string, details: any}>> {
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const lowStock = [];
    for (const [drug, details] of Object.entries(this.drugInventory)) {
      if (details.stock <= details.minLevel) {
        lowStock.push({ drug, details });
      }
    }
    return lowStock;
  }

  // Calculate medication cost
  static calculateMedicationCost(drugName: string, quantity: number): number {
    const drug = drugName.toLowerCase();
    const inventory = this.drugInventory[drug as keyof typeof this.drugInventory];
    return inventory ? inventory.cost * quantity : 0;
  }

  // Verify drug interactions (basic simulation)
  static async verifyDrugInteractions(medications: string[]): Promise<string[]> {
    await new Promise(resolve => setTimeout(resolve, 400));
    
    const interactions = [];
    const meds = medications.map(m => m.toLowerCase());
    
    // Basic interaction checks
    if (meds.includes('warfarin') && meds.includes('aspirin')) {
      interactions.push('MAJOR: Warfarin + Aspirin - Increased bleeding risk');
    }
    
    if (meds.includes('metformin') && meds.includes('insulin')) {
      interactions.push('MODERATE: Metformin + Insulin - Monitor blood glucose closely');
    }
    
    if (meds.includes('lisinopril') && meds.includes('potassium')) {
      interactions.push('MODERATE: ACE inhibitor + Potassium - Risk of hyperkalemia');
    }

    return interactions;
  }

  // Parse quantity from dosage string
  private static parseQuantityFromDosage(dosage: string, frequency: string): number {
    // Simple heuristic: assume 30-day supply for most medications
    const frequencyMultipliers: {[key: string]: number} = {
      'once daily': 30,
      'twice daily': 60,
      'three times daily': 90,
      'four times daily': 120,
      'every 8 hours': 90,
      'every 6 hours': 120,
      'as needed': 30,
      'prn': 30
    };

    const freq = frequency.toLowerCase();
    return frequencyMultipliers[freq] || 30; // Default to 30-day supply
  }

  // Get order status color for UI
  static getOrderStatusColor(status: string): string {
    switch (status) {
      case 'pending':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'verified':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'prepared':
        return 'text-purple-600 bg-purple-50 border-purple-200';
      case 'dispensed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'administered':
        return 'text-green-700 bg-green-100 border-green-300';
      case 'cancelled':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  }

  // Get inventory status color
  static getInventoryStatusColor(stock: number, minLevel: number): string {
    if (stock <= minLevel * 0.5) {
      return 'text-red-600 bg-red-50 border-red-200'; // Critical
    } else if (stock <= minLevel) {
      return 'text-orange-600 bg-orange-50 border-orange-200'; // Low
    } else if (stock <= minLevel * 2) {
      return 'text-yellow-600 bg-yellow-50 border-yellow-200'; // Adequate
    } else {
      return 'text-green-600 bg-green-50 border-green-200'; // Good
    }
  }

  // Generate dispensing report
  static generateDispensingReport(orders: PharmacyOrder[]): string {
    const reportHeader = `PHARMACY DISPENSING REPORT
Generated: ${new Date().toLocaleString()}
Total Orders: ${orders.length}
----------------------------------------\n`;

    const statusSummary = `STATUS SUMMARY:
Pending: ${orders.filter(o => o.status === 'pending').length}
Verified: ${orders.filter(o => o.status === 'verified').length}
Prepared: ${orders.filter(o => o.status === 'prepared').length}
Dispensed: ${orders.filter(o => o.status === 'dispensed').length}
Cancelled: ${orders.filter(o => o.status === 'cancelled').length}

`;

    const orderDetails = orders.map(order => 
      `Order ID: ${order.id}
Patient: ${order.patientId}
Status: ${order.status.toUpperCase()}
Quantity: ${order.dispensedQuantity || order.quantity}
Pharmacist: ${order.pharmacist || 'Unassigned'}
${order.completedAt ? `Dispensed: ${new Date(order.completedAt).toLocaleString()}` : ''}
Notes: ${order.notes || 'None'}
`).join('\n');

    return reportHeader + statusSummary + orderDetails;
  }

  // Simulate barcode scanning for medication verification
  static async scanMedicationBarcode(barcode: string): Promise<{
    medication: string;
    lot: string;
    expiry: string;
    verified: boolean;
  } | null> {
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Simulate barcode lookup
    const barcodeMap: {[key: string]: any} = {
      'MET123456': { medication: 'Metformin 500mg', lot: 'MET240827', expiry: '2025-08-27', verified: true },
      'LIS789012': { medication: 'Lisinopril 10mg', lot: 'LIS240825', expiry: '2025-12-15', verified: true },
      'WAR345678': { medication: 'Warfarin 5mg', lot: 'WAR240801', expiry: '2025-05-10', verified: true },
      'ASP901234': { medication: 'Aspirin 81mg', lot: 'ASP240820', expiry: '2026-02-20', verified: true },
      'INS567890': { medication: 'Insulin Glargine', lot: 'INS240826', expiry: '2024-12-26', verified: true }
    };

    return barcodeMap[barcode] || null;
  }

  // Get medication administration schedule
  static generateAdministrationSchedule(medications: Medication[]): Array<{
    time: string;
    medications: Array<{name: string, dose: string}>;
  }> {
    const schedule = [];
    const times = ['06:00', '12:00', '18:00', '22:00'];
    
    for (const time of times) {
      const medsAtTime = medications.filter(med => {
        const freq = med.frequency.toLowerCase();
        if (freq.includes('once daily') && time === '08:00') return true;
        if (freq.includes('twice daily') && (time === '08:00' || time === '20:00')) return true;
        if (freq.includes('three times') && (time === '08:00' || time === '14:00' || time === '20:00')) return true;
        if (freq.includes('four times') && ['08:00', '12:00', '16:00', '20:00'].includes(time)) return true;
        if (freq.includes('every 8 hours') && ['06:00', '14:00', '22:00'].includes(time)) return true;
        if (freq.includes('every 6 hours') && ['06:00', '12:00', '18:00'].includes(time)) return true;
        return false;
      });

      if (medsAtTime.length > 0) {
        schedule.push({
          time,
          medications: medsAtTime.map(med => ({
            name: med.name,
            dose: med.dosage
          }))
        });
      }
    }

    return schedule;
  }
}