const errMsg = document.querySelector('.error-msg');

function showError(err) {
    errMsg.classList.add('active');
    errMsg.textContent = err;
};


const form = document.getElementById('logInForm');
const apiTokenInput = form.querySelector('input[name="api_token"]');
const loadZonesButton = document.getElementById('loadZones');
const zonesSelect = form.querySelector('select[name="zones"]');

function appendZones(zones) {
    zones.forEach(zone => {
        zonesSelect.innerHTML += `<option value="${zone.name}">${zone.name}</option>`;
    });
}

loadZonesButton.addEventListener('click', (e) => {
    const params = new URLSearchParams({ api_token: apiTokenInput.value });
    fetch(`${window.location.origin}/cf/load-zones?${params.toString()}`)
    .then(async res => {
        const resData = await res.json();
        if (!res.ok) return showError(resData.message);
        const zones = resData.zones;
        console.log(zones)
        appendZones(zones);
    })
    .catch(err => showError(err));
})

form.addEventListener('submit', (e) => {
    e.preventDefault();

    fetch(`${window.location.origin}/cf/set-config`, {
        method: 'POST',
        headers: {
            'Content-type': 'application/json'
        },
        body: JSON.stringify({ 'api_token': apiTokenInput.value, 'zone_name': zonesSelect.value })
    })
    .then(async res => {
        const resData = await res.json();
        if (!res.ok) return showError(resData?.message);
        tunnelBlock.activateBlock(resData?.zones);
    })
    .catch(err => showError(err));
})





