class LogInBlock {
    constructor(tunnelBlock) {
        this.tunnelBlock = tunnelBlock;
        this.form = document.getElementById('logInForm');
        this.tokenInput = this.form.querySelector('input[name="api_token"]');
        this.errMsg = this.form.querySelector('p.error-msg');

        this.form.addEventListener('submit', this.onSubmit.bind(this));
    }

    showError(text) {
        this.errMsg.textContent = text;
        if (!this.errMsg.classList.contains('active')) this.errMsg.classList.add('active');
    }

    onSubmit(e) {
        e.preventDefault();
        const api_token = this.tokenInput.value;
        if (api_token.length < 10) {
            this.errMsg.style.display = 'block';
            return this.errMsg.textContent = 'Token is too short';
        }
        
        fetch(`${window.location.origin}/cf-log-in`, {
            method: 'POST',
            headers: {
                'Content-type': 'application/json'
            },
            body: JSON.stringify({api_token})
        })
        .then(async res => {
            const resData = await res.json();
            if (!res.ok) return this.showError(resData?.message);
            this.tunnelBlock.activateBlock(resData?.zones);
        })
        .catch(err => {
            this.showError(err);
        })
    }
}


class TunnelBlock {
    constructor() {
        this.zones = {};
        this.form  = document.getElementById('zoneSelectForm');
        this.select = this.form.querySelector('select[name="zones"]');
        this.errMsg = this.form.querySelector('p.error-msg');

        this.form.addEventListener('submit', this.onSubmit.bind(this));
    }

    showError(text) {
        this.errMsg.textContent = text;
        if (!this.errMsg.classList.contains('active')) this.errMsg.classList.add('active');
    }

    activateBlock(zones) {
        console.log(zones)
        this.zones = zones;
        for (let zone in zones) {
            this.select.innerHTML += `<option value="${zone}">${zone}</option>`;
        }
    }

    onSubmit(e) {
        e.preventDefault();
        const zone = this.select.value;

        fetch(`${window.location.origin}/cf-create-tunnel`, {
            method: 'POST',
            headers: {
                'Content-type': 'application/json'
            },
            body: JSON.stringify({ zone: this.zones[zone] })
        })
        .then(async res => {
            const resData = await res.json();
            if (!res.ok) return this.showError(resData?.message);
            
        })
        .catch(err => {
            this.showError(err);
        })
    }
}

const tunnelBlock = new TunnelBlock();
const logInBlock = new LogInBlock(tunnelBlock);







