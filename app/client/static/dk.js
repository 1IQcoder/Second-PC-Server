class NewDkForm {
    constructor() {
        this.form = document.getElementById('newDk');
        this.nameInput = this.form.querySelector('input[name="name"]');
        this.urlInput = this.form.querySelector('input[name="url"]');
        this.tokenInput = this.form.querySelector('input[name="token"]');
        this.branchInput = this.form.querySelector('input[name="branch"]');
        this.portInput = this.form.querySelector('input[name="port"]');
        this.errMsg = this.form.querySelector('.error-msg');

        this.form.addEventListener('submit', this.onSubmit.bind(this));
    }

    showError(text) {
        this.errMsg.textContent = text;
        if (!this.errMsg.classList.contains('active')) this.errMsg.classList.add('active');
    }

    onSubmit(e) {
        e.preventDefault();

        fetch(`${window.location.origin}/dk/launch`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: this.nameInput.value,
                url: this.urlInput.value,
                token: this.tokenInput.value,
                branch: this.branchInput.value,
                port: this.portInput.value
            })
        })
        .then(async res => {
            const resData = await res.json();
            if (res.ok) return this.showError(resData?.message);
            this.showError(resData?.message);
        })
        .catch(err => this.showError(err));
    }
}

const newDkForm = new NewDkForm();






