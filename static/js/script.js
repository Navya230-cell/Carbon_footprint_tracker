// static/js/script.js

function logActivity() {
    const data = {
        user_id: 1,
        activity_id: 2,
        quantity: 10,
        notes: "Morning commute"
    };

    fetch('http://127.0.0.1:5000/add_activity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        document.getElementById('emissionDisplay').innerText = 
            `Carbon emission: ${result.total_emission} kg CO₂`;
    })
    .catch(error => console.error(error));
}
