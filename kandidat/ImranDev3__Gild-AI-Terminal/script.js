// GILD-AI Live Dashboard Logic
async function fetchTradingData() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/data');
        const data = await response.json();
        
        document.getElementById('price').innerText = `$${data.price}`;
        document.getElementById('signal').innerText = data.signal;
        
        console.log("Market Data Updated:", data);
    } catch (error) {
        console.error("Connection to GILD-AI Engine failed.");
    }
}

// Update data every 5 seconds
setInterval(fetchTradingData, 5000);