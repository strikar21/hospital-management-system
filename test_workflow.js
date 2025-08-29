// Simple test script to verify backend APIs work
const baseUrl = 'http://localhost:8001';
const authToken = 'demo-token';

async function testAPI(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${baseUrl}${endpoint}`, options);
        const result = await response.text();
        console.log(`${method} ${endpoint}: ${response.status} - ${result.substring(0, 200)}...`);
        return { status: response.status, data: result };
    } catch (error) {
        console.error(`Error testing ${endpoint}:`, error.message);
        return { error: error.message };
    }
}

// Test workflow
async function testWorkflow() {
    console.log('=== Testing Hospital Backend APIs ===');
    
    // Test 1: Basic connectivity
    await testAPI('/');
    
    // Test 2: Authentication test
    await testAPI('/api/v1/mobile/test');
    
    // Test 3: Patient list
    await testAPI('/api/v1/mobile/patients?limit=5');
    
    // Test 4: Dashboard overview
    await testAPI('/api/v1/mobile/dashboard/overview');
    
    // Test 5: Patient creation
    const patientData = {
        id: 'test-patient-' + Date.now(),
        name: 'Test Patient',
        age: 30,
        gender: 'Male',
        bed_number: '101-A',
        ward: 'ICU',
        room: '101',
        department: 'Emergency',
        assigned_doctor: 'Dr. Test',
        diagnosis: 'Test condition',
        admission_date: new Date().toISOString()
    };
    
    await testAPI('/api/v1/mobile/patients', 'POST', patientData);
    
    console.log('=== Test Complete ===');
}

testWorkflow();