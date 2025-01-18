class ApiResponse {
    /**
     * API request result object
     * @param {boolean} success
     * @param {string} msg
     */
    constructor(success, msg) {
        this.success = success;
        this.msg = msg;
    }
}

/** AccountObject
 * @typedef {object} AccountObject
 * @property {string} username
 * @property {string} name
 * @property {string} access_token
 */


/** RepoObject
 * @typedef {object} RepoObject
 * @property {string} url
 * @property {string} privateUrl
 * @property {string} fullName
 * @property {string} ownerName
 * @property {string} repoName
 * @property {string} name
 * @property {string} branchName
 * @property {boolean} isPrivate
 * @property {AccountObject} account
 * @property {object} git
 * @property {boolean} git.isPulled
 * @property {string} git.commitHash
 * @property {object} docker
 * @property {string} docker.imageName
 * @property {string} docker.rootPath
 * @property {string} docker.buildCommand
 * @property {boolean} docker.isBuilded
 * @property {boolean} docker.isRunning
 * @property {string} docker.containerStatus
 * @property {object} docker.ports
 * @property {string} docker.ports.locall
 * @property {string} docker.ports.container
 * @property {string} docker.runCommand
 */


class AccountsController {
    constructor() {
        this.accountList = {};
    }

    /**
     * @returns {object | ApiResponse} // return null if no accounts, else object of {AccountObject}
     */
    async loadAccounts() {
        const res = await fetch(`${SERVER_URL}/api/get-accounts`, { method: 'GET' });
        const resData = await res.json();
        if (res.status == 200 && resData.msg) return new ApiResponse(true, 'accounts list empty');   // accounts list empty
        if (res.status != 200) return new ApiResponse(false, `Load accounts error: ${resData.msg}`);
        this.accountList = resData;
        return resData;
    }

    /**
     * Adds a new account on the server
     * @param {AccountObject} accountObj
     * @returns {ApiResponse}
     */
    async addAccount(accountObj) {
        const params = new URLSearchParams({ account: JSON.stringify(accountObj) });

        const res = await fetch(`${SERVER_URL}/api/new-account?${params.toString()}`, { method: 'GET' });
        const resData = await res.json();
        if (res.status != 200) return new ApiResponse(false, resData.msg);
        this.accountList[accountObj.username] = accountObj;
        return new ApiResponse(true, resData.msg);
    }

    /**
     * @param {string} accountUsername
     * @returns {ApiResponse}
     */
    async deleteAccount(accountUsername) {
        const params = new URLSearchParams({ username: accountUsername })
        const res = await fetch(`${SERVER_URL}/api/delete-account?${params.toString()}`)
        const resData = await res.json();
        if (!res.ok) return new ApiResponse(false, resData.msg);
        delete this.accountList[accountUsername];
        return new ApiResponse(true, resData.msg);
    }

    /**
     * @param {string} accountUsername
     * @returns { { success: boolean, account: AccountObject } | { success: boolean, msg: string } } return error msg if error occured
     */
    async getAccount(accountUsername) {
        const params = new URLSearchParams({ username: accountUsername });
        const res = await fetch(`${SERVER_URL}/api/get-repo?${params.toString()}`, { method: 'GET' });
        const resData = await res.json();
        if (res.status != 200) return { success: false, msg: resData.msg };
        console.log(resData)
        return { success: true, resData };
    }
}

class AccountsRenderer {
    /**
     * @param {string} selector 
     * @param {AccountsController} controller 
     */
    constructor(selector, controller) {
        this.controller = controller;
        this.section = document.querySelector(selector);

        this.state = {
            isAddingAccount: false,
            accounts: {} // HTML element references
        };

        this.ui = {
            accountsContainer: this.createAccountsProxy(),
            addAccountForm: this.createAddAccountProxy(),
            addButton: this.section.querySelector('#accounts__addButton'),
            closeButton: this.section.querySelector('#accounts__closeButton'),
            errorMsg: this.section.querySelector('.accounts__newWrapper__errMsg')
        };

        this.initialize();
    }

    initialize() {
        this.renderAccounts();
        this.ui.addAccountForm.hide();

        this.ui.addButton.addEventListener('click', () => this.handleAddButtonClick());
        this.ui.closeButton.addEventListener('click', () => this.ui.addAccountForm.hide());
    }

    async deleteAccount(username) {
        const res = await this.controller.deleteAccount(username);
        if (!res.success) return terminal.addMsg(400, res.msg);
        this.state.accounts[username].remove();
        terminal.addMsg(200, res.msg);
    }

    createAddAccountProxy() {
        const form = this.section.querySelector('.accounts__newWrapper');
        return {
            form,
            hide: () => {
                form.style.display = 'none';
                this.state.isAddingAccount = false;
                this.ui.closeButton.style.display = 'none';
                this.ui.addButton.textContent = 'Add account';
            },
            show: () => {
                form.style.display = 'flex';
                this.state.isAddingAccount = true;
                this.ui.closeButton.style.display = 'block';
                this.ui.addButton.textContent = 'Confirm ✓';
                this.ui.errorMsg.textContent = '';
            }
        };
    }

    createAccountsProxy() {
        const container = this.section.querySelector('.accounts__wrapper');
        return {
            container,
            /**
             * @param {AccountObject} accountObj 
             */
            appendAccount: (accountObj) => {
                const blockId = Date.now();

                container.innerHTML += `
                    <div id="${blockId}" class="--basicSection__block" data-username="${accountObj.username}">
                        <h3>${accountObj.username} (${accountObj.name})</h3>
                        <span>access_token: ${accountObj.access_token}</span>
                        <br>
                        <button id="delete_${blockId}" style="background-color: red;">Delete</button>
                    </div>
                    <br>
                `;

                const accountBlock = this.ui.accountsContainer.container.querySelector(`#${CSS.escape(blockId)}`);
                this.state.accounts[accountObj.username] = accountBlock;
                const deleteButton = accountBlock.querySelector(`#delete_${blockId}`);
                deleteButton.addEventListener('click', () => this.deleteAccount(accountObj.username));
            }
        };
    }

    async renderAccounts() {
        const data = await this.controller.loadAccounts();
        if (data.success) return terminal.addMsg(200, 'Account list empty');
        if (data.success && data.success == false) return terminal.addMsg(400, data.msg);
        Object.values(data).forEach(account => {
            this.ui.accountsContainer.appendAccount(account);
        });

        terminal.addMsg(200, 'Accounts list loaded');
    }

    async handleAddButtonClick() {
        if (!this.state.isAddingAccount) {
            this.ui.addAccountForm.show();
            return;
        }

        const username = this.ui.addAccountForm.form.querySelector('input[name="username"]').value;
        const access_token = this.ui.addAccountForm.form.querySelector('input[name="access_token"]').value;

        if (!access_token) {
            this.ui.errorMsg.textContent = 'access_token and username are required';
            return;
        }

        const user = await (await fetch(`https://api.github.com/users/${username}`)).json();
        if (user.status === 404) {
            this.ui.errorMsg.textContent = 'user not found';
            return;
        }

        const account = {
            username,
            name: user.name,
            access_token
        };

        const res = await this.controller.addAccount(account);
        if (!res.success) return terminal.addMsg(400, res.msg);

        this.ui.accountsContainer.appendAccount(account);
        this.ui.addAccountForm.hide();
        terminal.addMsg(200, res.msg);
    }
}

class ReposController {
    constructor() {
        this.vars = {
            repos: {}   // stores object with repos names
        }
    }

    /**
     * @param {string} repoName 
     * @returns {RepoObject | ApiResponse}
     */
    async getRepo(repoName) {
        const params = new URLSearchParams({ repo_name: repoName });
        const res = await fetch(`${SERVER_URL}/api/get-repo?${params.toString()}`, { method: 'GET' });
        const resData = await res.json();
        if (res.status != 200) return new ApiResponse(false, resData.msg);
        return resData;
    }

    /**
     * @param {string} repoName 
     * @returns {ApiResponse}
     */
    async deleteRepo(repoName) {
        const params = new URLSearchParams({ repo_name: repoName });
        const res = await fetch(`${SERVER_URL}/api/delete-repo?${params.toString()}`, { method: 'GET' });
        const resData = await res.json();
        if (res.status != 200) return new ApiResponse(false, resData.msg);
        return new ApiResponse(true, resData.msg);
    }

    /**
     * @param { { msg: Function, error: Function, repoObj: Function } } callback
     */
    async getRepos(callback) {
        const eventSource = new EventSource(`${SERVER_URL}/api/get-repos`);
        
        eventSource.onopen = () => {
            if (callback.msg) callback.msg('Getting repos');
        }

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type == 'close') {
                if (data.msg) callback.msg(data.msg);
                return eventSource.close();
            }
            
            if (data.type == 'json') {
                const repoObj = JSON.parse(data.data);
                callback.repoObj(repoObj);
            }
        }

        eventSource.onerror = (err) => {
            if (callback.error) callback.error(`Load repos error: ${err}`);
            return eventSource.close();
        }
    }
}

class ReposRenderer {
    /**
     * @param {string} selector 
     * @param {ReposController} controller 
     */
    constructor(selector, controller) {
        this.controller = controller;
        this.section = document.querySelector(selector);

        this.state = {
            repos: {},  // HTML element references
            isAddRepoOpen: false
        };

        this.ui = {
            reposWrapper: this.section.querySelector('.reposList__wrapper'),
            updateButton: this.section.querySelector('.repos_updateButton'),
            newRepoWrapper: this.section.querySelector('.reposList__newRepoWrapper'),
            addRepoButton: this.section.querySelector('#reposList__addRepoButton'),
            closeRepoButton: this.section.querySelector('#reposList__closeRepoButton'),
            errorMessage: this.section.querySelector('.reposLis__newRepoWrapper__errMsg'),
            repoUrlInput: this.section.querySelector('input[name="repo_url"]'),
            branchSelect: this.createBranchSelect(),
            isPrivateRepoInput: this.section.querySelector('input[name="isPrivateRepo"]'),
            accountSelectDiv: this.section.querySelector('.newRepo__accountSelectDiv'),
            accountSelect: this.createAccountSelect(),
            dockerFilePathInput: this.section.querySelector('input[name="dockerfilepath"]')
        };

        this.init();
    }

    init() {
        this.renderRepos();
        this.ui.closeRepoButton.style.display = 'none';
        this.ui.newRepoWrapper.style.display = 'none';
        this.ui.accountSelectDiv.style.display = 'none';

        this.ui.branchSelect.element.addEventListener('focus', e => this.handleBranchFocus(e));
        this.ui.closeRepoButton.addEventListener('click', () => this.toggleAddRepoSection(false));
        this.ui.addRepoButton.addEventListener('click', () => this.handleAddRepo());
        this.ui.isPrivateRepoInput.addEventListener('change', e => this.toggleAccountSelect(e));
        this.ui.updateButton.addEventListener('click', () => this.refreshRepos());
    }

    createBranchSelect() {
        const select = this.section.querySelector('select[name="branch"]');
        return {
            element: select,
            addOption(value, text, clear = false) {
                if (clear) select.innerHTML = '';
                const option = document.createElement('option');
                option.value = value;
                option.textContent = text;
                select.appendChild(option);
            },
            clearOptions() {
                select.innerHTML = '';
            }
        };
    }

    createAccountSelect() {
        const select = this.section.querySelector('select[name="account"]');
        return {
            element: select,
            async update() {
                select.innerHTML = '';
                const accounts = accountsController.accountList;
                console.log(accounts)
                if (accounts.length === 0) {
                    select.innerHTML = `<option value="1">No accounts available</option>`;
                    return;
                }

                for (const key of Object.keys(accounts)) {
                    const account = accounts[key];
                    select.innerHTML += `<option value="${account.username}">${account.username} (${account.name})</option>`;
                }
            }
        };
    }

    async displayRepo(repo) {
        const blockId = Date.now();
        this.ui.reposWrapper.innerHTML += `
            <br>
            <div class="reposList__wrapper__elem" id="${blockId}">
                <h3>Repo: ${repo.repoName} Owner: ${repo.ownerName} Branch: ${repo.branchName}</h3>
                <br>
                <div class="reposList__wrapper__elem__table">
                    <div><span>Downloaded</span><span>False</span></div>
                    <div><span>Builded</span><span>False</span></div>
                    <div><span>Container</span><span>None</span></div>
                    <div><span>Ports</span><span>----/----</span></div>
                </div>
                <br>
                <div style="display: inline-flex;">
                    <button data-id="${blockId}" onclick="switchRepoSettings(this)">Edit settings</button>
                    <button data-repo="${repo.name}" onclick="fullLaunch(this)" style="margin-left: 10px; margin-right: 10px;">Run container</button>
                    <button data-id="${blockId}" data-repo="${repo.name}" onclick="delete_repo(this)" style="background-color: red;">Delete repo</button>
                </div>
                <br>
                <div class="reposList__wrapper__elem__settings">
                    <div><span>rootPath:</span><input type="text" value="${repo.docker.rootPath}"><button>edit</button></div>
                    <div><span>buildCommand:</span><input type="text" value="${repo.docker.buildCommand}"><button>edit</button></div>
                    <div><span>runCommand:</span><input type="text" value="${repo.docker.runCommand}"><button>edit</button></div>
                    <div><span>Local port:</span><input type="text" value=""><button>edit</button></div>
                    <div><span>In docker port:</span><input type="text" value=""><button>edit</button></div>
                </div>
            </div>
        `;
    }

    async renderRepos() {
        const callback = {
            msg: (msg) => {
                terminal.addMsgToBlock(msg);
            },
            error: (err) => {
                terminal.addMsgToBlock(err);
            },
            repoObj: (repoObj) => {
                this.displayRepo(repoObj);
            }
        }
        terminal.addMsgBlock('Updating repositories...');
        this.controller.getRepos(callback);
    }

    async refreshRepos() {
        const response = await fetch(`${SERVER_URL}/api/update-repos-state`);
        const data = await response.json();
        if (data.message && response.status === 200) {
            return;
        }
        data.forEach(repo => {
            // Logic for updating repositories can be implemented here
        });
    }

    async handleBranchFocus() {
        const select = this.ui.branchSelect;
        const repoUrl = this.ui.repoUrlInput.value;
        if (!repoUrl) {
            this.ui.errorMessage.textContent = 'Invalid repository URL';
            return;
        }

        const repoName = repoUrl.slice(repoUrl.lastIndexOf('.com/') + 5, -4);
        const fetchUrl = `https://api.github.com/repos/${repoName}/branches`;
        const headers = this.ui.isPrivateRepoInput.checked ? await this.getAuthHeaders() : null;

        fetch(fetchUrl, { method: 'GET', headers })
            .then(res => res.ok ? res.json() : Promise.reject('Error fetching branches'))
            .then(branches => {
                select.clearOptions();
                if (!branches.length) {
                    this.ui.errorMessage.textContent = 'No branches available';
                } else {
                    branches.forEach(branch => select.addOption(branch.name, branch.name));
                }
            })
            .catch(err => this.ui.errorMessage.textContent = err);
    }

    async getAuthHeaders() {
        const accounts = accountsController.accountList;
        const account = accounts[this.ui.accountSelect.element.value];
        return {
            'Authorization': `Bearer ${account.access_token}`,
            'Accept': 'application/vnd.github.v3+json'
        };
    }

    toggleAddRepoSection(isOpen) {
        this.state.isAddRepoOpen = isOpen;
        this.ui.newRepoWrapper.style.display = isOpen ? 'flex' : 'none';
        this.ui.closeRepoButton.style.display = isOpen ? 'block' : 'none';
        this.ui.addRepoButton.textContent = isOpen ? 'Confirm ✓' : 'Add repository';

        if (isOpen) {
            this.ui.branchSelect.clearOptions();
            this.ui.accountSelectDiv.style.display = 'none';
            this.ui.isPrivateRepoInput.checked = false;
            this.ui.accountSelect.element.value = false;
        }
    }

    toggleAccountSelect(e) {
        this.ui.accountSelectDiv.style.display = e.target.checked ? 'flex' : 'none';
        if (e.target.checked) this.ui.accountSelect.update();
    }

    async handleAddRepo() {
        if (this.state.isAddRepoOpen && this.ui.newRepoWrapper.style.display === 'none') {
            this.toggleAddRepoSection(false);
            return;
        }
        if (!this.state.isAddRepoOpen && this.ui.newRepoWrapper.style.display === 'none') {
            this.toggleAddRepoSection(true);
            return;
        }

        const repoUrl = this.ui.repoUrlInput.value;
        const branch = this.ui.branchSelect.element.value;
        if (!repoUrl || !branch) {
            this.ui.errorMessage.textContent = 'URL and branch are required';
            return;
        }

        const match = repoUrl.match(/github\.com\/([^\/]+)\/([^\/.]+)/);
        if (!match) {
            this.ui.errorMessage.textContent = 'Invalid URL';
            return;
        }

        const [_, owner, repo] = match;
        const repoFullName = `${owner}/${repo}`;
        const repoNameWithBranch = `${owner}.${repo}.${branch}`;
        const isPrivate = this.ui.isPrivateRepoInput.checked;
        const dockerFilePath = this.ui.dockerFilePathInput.value.replace(/^\//, '');
        const ports = {
            local: this.ui.newRepoWrapper.querySelector('input[name="dockerPort"]').value,
            container: this.ui.newRepoWrapper.querySelector('input[name="locallPort"]').value
        };

        let account = {};
        let accessToken = '';
        if (isPrivate) {
            account = JSON.parse(window.localStorage.getItem('accounts'))[this.ui.accountSelect.element.value];
            accessToken = account.access_token;
        }
        const privateRepoUrl = `https://${accessToken}@github.com/${owner}/${repo}.git`;

        const repoData = {
            url: repoUrl,
            privateUrl: privateRepoUrl,
            fullName: repoFullName,
            ownerName: owner,
            repoName: repo,
            name: repoNameWithBranch,
            branchName: branch,
            isPrivate,
            account: {
                username: isPrivate ? account.username : '-',
                name: isPrivate ? account.name : '-',
                access_token: isPrivate ? accessToken : '-'
            },
            git: { isPulled: false, commitHash: 1 },
            docker: {
                imageName: repoNameWithBranch.toLowerCase(),
                rootPath: dockerFilePath,
                buildCommand: `docker build -t ${repoNameWithBranch.toLowerCase()}:latest ${dockerFilePath} --no-cache`,
                isBuilded: false,
                isRunning: false,
                containerStatus: 'offline',
                ports,
                runCommand: `docker run --name ${repoNameWithBranch.toLowerCase()} -d -p ${ports.local}:${ports.container} ${repoNameWithBranch.toLowerCase()}:latest`
            }
        };

        this.state.repos[repoNameWithBranch] = repoData;
        window.localStorage.setItem('repos', JSON.stringify(this.state.repos));

        const params = new URLSearchParams({ repo: JSON.stringify(repoData) });
        const response = await fetch(`${SERVER_URL}/api/new-repo?${params}`, { method: 'GET' });
        const result = await response.json();

        if (!response.ok) {
            terminal.addMsg(400, result.message);
            return;
        }
        terminal.addMsg(200, result.message);

        this.displayRepo(repoData);
        this.toggleAddRepoSection(false);
    }
}

class Terminal {
    constructor(selector) {
        this.section = document.querySelector(selector);

        this.vars = {
            isResizing: false,
            autoScroll: false,  // отвечает за автоматическую прокрутку вниз
            terminalPos: 'bottom',
            terminalWidth: 500,
            terminalHeight: 200,
            curMsgBlock: null,
        }

        this.elements = {
            msgWrapper: this.section.querySelector('.terminal_messagesWrapper'),
            positionButton: this.section.querySelector('.terminal_positionButton'),
            clearButton: this.section.querySelector('.terminal__clearButton'),
            autoScrollButton: this.section.querySelector('.terminal__autoScrollButton'),
            resizer: this.section.querySelector('#terminal_resizer'),
        }

        this.resizeTerminal = this.resizeTerminal.bind(this);
        this.stopResizeTerminal = this.stopResizeTerminal.bind(this);

        this.init();
    }

    init() {
        this.positionButtonListener();
        this.elements.clearButton.addEventListener('click', () => this.handleClearButton());
        this.elements.resizer.addEventListener('mousedown', () => this.handleResizer());
        this.elements.autoScrollButton.addEventListener('click', () => this.autoScrollButtonListener());
        this.elements.positionButton.addEventListener('click', () => this.positionButtonListener());
    }

    // FUNCTIONS
    scrollDown() {
        if (this.vars.autoScroll) {
            this.elements.msgWrapper.scrollTop = this.elements.msgWrapper.scrollHeight;
        }
    }

    addMsg(status, msg) {
        const now = new Date();
        const formatted = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

        let msgType
        if (status == 200 || status == 'ok') {
            msgType = 'ok'
        } else if (status == 400 || status == 'err') {
            msgType = 'err'
        } else if (status == 'warn') {
            msgType = 'warn'
        }

        this.elements.msgWrapper.innerHTML += `
            <div class="${msgType}">
                <span>[${formatted}] </span><span>${msg}</span>
            </div>
            <br>
        `
        this.scrollDown();
    }

    addMsgBlock(title, content) {
        const blockId = Date.now();

        this.elements.msgWrapper.innerHTML += `
            <div class="block" id="${blockId}">
                <h4 onclick="hideContent(this)" data-id="${blockId}">${title}</h4>
                <div class="block_content">
                    ${content != null ? `<span>${content}</span>` : ''}
                </div>
            </div>
            <br>
        `
        this.vars.curMsgBlock = this.elements.msgWrapper.querySelector(`#${CSS.escape(blockId)}>.block_content`);
        this.scrollDown();
    }

    closeMsgBlock = () => { this.vars.curMsgBlock = null; }

    addMsgToBlock(msg) {
        console.log(msg)
        if (this.vars.curMsgBlock) {
            this.vars.curMsgBlock.innerHTML += `<span>${msg}</span>`;
        }
    }
    
    resizeTerminal(e) {
        if (!this.vars.isResizing) return;

        if (this.vars.terminalPos == 'bottom') {
            const newHeight = window.innerHeight - e.clientY;
            this.section.style.height = `${newHeight}px`;
        } else if (this.vars.terminalPos == 'right') {
            const newWidth = window.innerWidth - e.clientX;
            this.section.style.width = `${newWidth}px`;
        }
    }

    stopResizeTerminal() {
        document.body.style.userSelect = 'text';
        this.vars.isResizing = false;
        document.body.style.cursor = '';
        document.removeEventListener('mousemove', this.resizeTerminal);
        document.removeEventListener('mouseup', this.stopResizeTerminal);
    }

    // EVENT LISTENERS
    handleClearButton() {
        this.elements.msgWrapper.innerHTML = ''
    }

    handleResizer() {
        document.body.style.userSelect = 'none';
        this.vars.isResizing = true
        document.addEventListener('mousemove', this.resizeTerminal)
        document.addEventListener('mouseup', this.stopResizeTerminal)
    }

    autoScrollButtonListener() {
        if (this.vars.autoScroll) {
            this.vars.autoScroll = false;
            this.elements.autoScrollButton.textContent = 'autoScroll ✓';
        } else {
            this.vars.autoScroll = true;
            this.elements.autoScrollButton.textContent = 'autoScroll ✕';
        }
    }

    positionButtonListener() {
        if (this.vars.terminalPos == 'bottom') {
            this.vars.terminalHeight = this.section.offsetHeight;
            this.vars.terminalPos = 'right';

            this.section.classList.remove('bottom');
            this.section.classList.add('right');

            this.elements.positionButton.textContent = 'right';
            this.section.style.height = `${window.innerHeight}px`;
            this.section.style.width = `${this.vars.terminalWidth}px`;
        } else {
            this.vars.terminalWidth = this.section.offsetWidth;
            this.vars.terminalPos = 'bottom';

            this.section.classList.remove('right');
            this.section.classList.add('bottom');

            this.elements.positionButton.textContent = 'bottom';
            this.section.style.width = `${window.innerWidth}px`;
            this.section.style.height = `${this.vars.terminalHeight}px`;
        }
    }
}

const terminal = new Terminal('.terminal');
const accountsController = new AccountsController();
const accountsRenderer = new AccountsRenderer('.accounts', accountsController);
const reposController = new ReposController();
const reposRenderer = new ReposRenderer('.reposList', reposController);




