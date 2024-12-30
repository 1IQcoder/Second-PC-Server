class ReposList {
    constructor(selector) {
        this.section = document.querySelector(selector);

        this.vars = {
            repos: {},
            isNewRepoSectionOpen: false
        }

        this.elements = {
            repos_wrapper: this.section.querySelector('.reposList__wrapper'),
            newRepo_wrapper: this.section.querySelector('.reposList__newRepoWrapper'),
            newRepo_addButton: this.section.querySelector('#reposList__addRepoButton'),
            newRepo_closeButton: this.section.querySelector('#reposList__closeRepoButton'),
            newRepo_errMsg: this.section.querySelector('.reposLis__newRepoWrapper__errMsg'),
            newRepo_urlInput: this.section.querySelector(' input[name="repo_url"]'),
            newRepo_branchSelect: this.createBranchSelectProxy(),
            newRepo_isPrivateRepoInput: this.section.querySelector(' input[name="isPrivateRepo"]'),
            newRepo__accountSelectDiv: this.section.querySelector('.newRepo__accountSelectDiv'),
            newRepo_accountSelect: this.accountSelectProxy(),
            newRepo_dockerfilepathInput: this.section.querySelector(' input[name="dockerfilepath"]')
        };

        this.init();
    }

    init() {
        this.loadRepos();
        this.elements.newRepo_closeButton.style.display = 'none';
        this.elements.newRepo_wrapper.style.display = 'none';
        this.elements.newRepo__accountSelectDiv.style.display = 'none';

        this.elements.newRepo_branchSelect.e.addEventListener('focus', e => this.handleBranchSelect(e))
        this.elements.newRepo_closeButton.addEventListener('click', () => this.handleCloseButton())
        this.elements.newRepo_addButton.addEventListener('click', () => this.handleAddButton())
        this.elements.newRepo_isPrivateRepoInput.addEventListener('change', (e) => this.handleIsPrivateRepoInput(e))
    }

    // FUNCTIONS
    createBranchSelectProxy() {
        const self = this;
        const select = self.section.querySelector('select[name="branch"]');

        return {
            get e() {
                return select
            },

            appendOption(value, text, clear=false) {
                if (clear) {
                    select.innerHTML = ''
                }
                const option = document.createElement('option');
                option.value = value;
                option.textContent = text;
                select.appendChild(option);
            },

            clearOptions() {
                select.innerHTML = ''
            }
        };
    }

    accountSelectProxy() {
        const select = this.section.querySelector(' select[name="account"]');

        return {
            e: select,

            update: async () => {
                select.innerHTML = ''
                const accountsStr = window.localStorage.getItem('accounts')
                const accounts = JSON.parse(accountsStr);
                console.log(accounts);
                if (accounts.length < 1) {
                    select.innerHTML = `<option value="1">you havent any account</option>`
                }
                for (const key in accounts) {
                    const account = accounts[key];
                    select.innerHTML += `<option value="${account.username}">${account.username} (${account.name})</option>`;
                }
            }
        }
    }


    async spawnRepo(repo) {
        const blockId = Date.now();

        this.elements.repos_wrapper.innerHTML += `
            <br>
            <div id="${blockId}" class="reposList__wrapper__elem" data-repo_name="${repo.name}">
                <div style="display: flex; flex-direction: column;">
                    <h3>${repo.name} (${repo.branchName})</h3>
                    <a href="${repo.url}">${repo.url} ⇱</a>
                    <br>
                    <span>private: ${repo.isPrivate}</span>
                    <span>account: ${repo.account.username} (${repo.account.name})</span>
                    <span>last downloaded commit: ${repo.git.commitHash}</span>
                    <br>
                    <ul>
                        <h4>docker info:</h4>
                        <li>container: ${repo.docker.isBuilded == true ? `builded/${repo.docker.status}` : '-'}</li>
                        <li><span>build command:</span><input name="buildCommandInput" type="text" value="${repo.docker.buildCommand}"><button data-id="${blockId}" onclick="updateBuildCommand(this)">save</button></li>
                        <li><span>run command:</span><input type="text" value="${repo.docker.runCommand}"></li>
                    </ul>
                </div>
                <div class="reposList__wrapper__elem__buttonsWrapper">
                    <button class="git_pull" data-id="${blockId}" onclick="git_pull(this)">git pull</button>
                    <button class="docker_build" data-id="${blockId}" onclick="docker_build(this)">docker build</button>
                    <button class="docker_run" data-id="${blockId}" onclick="docker_run(this)">docker run</button>
                    <button class="pull_and_run" data-id="${blockId}" onclick="pull_and_run(this)">pull and run</button>
                    <button class="delete-repo" data-id="${blockId}" onclick="delete_repo(this)" style="background-color: red;">delete</button>
                </div>
            </div>
        `
    }


    async loadRepos() {
        const res = await fetch(`${SERVER_URL}/api/get-repos`, { method: 'GET' });
        const resData = await res.json();
        if (!res.ok) {
            return terminal.addMsg(400, resData.message);
        }
        if (resData?.message) {
            return terminal.addMsg(200, resData?.message || 'repositories loaded')
        }
        resData.forEach(repo => {
            if (!repo) {
                return;
            }
            this.vars.repos[repo.name] = repo;
            this.spawnRepo(repo);
        });
    }

    // EVENT LISTENERS
    async handleBranchSelect(e) {
        const select = this.elements.newRepo_branchSelect
        const repo_url = this.elements.newRepo_urlInput.value
    
        if (!repo_url) {
            this.elements.newRepo_errMsg.textContent = 'invalid repository url'
            return;
        }
    
        const repoName = repo_url.slice(repo_url.lastIndexOf('.com/')+5, repo_url.length-4)
        console.log(repoName);
        const fetchBranchesUrl = `https://api.github.com/repos/${repoName}/branches`;
        let headersObj;

        if (this.elements.newRepo_isPrivateRepoInput.checked) {
            const accounts = await JSON.parse(window.localStorage.getItem('accounts'));
            const account = accounts[this.elements.newRepo_accountSelect.e.value];
            
            headersObj = {
                'Authorization': `Bearer ${account.access_token}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        }

        fetch(fetchBranchesUrl, {
            method: 'GET',
            headers: headersObj ?? ''
        })
        .then(res => {
            if (!res.ok) {
                select.appendOption('1', 'error occured');
                return Promise.reject('bad responce');
            }
            select.appendOption('1', 'loading...');
            return res.json();
        })
        .then(res => {
            select.clearOptions()
            if (res.length == 0) {
                this.elements.newRepo_errMsg.textContent = 'this repository have no branch';
                return;
            }
            res?.forEach(e => {
                select.appendOption(e.name, e.name);
            });
        })
        .catch(err => {
            this.elements.newRepo_errMsg.textContent = err;
        })
    }

    handleCloseButton() {
        this.elements.newRepo_wrapper.style.display = 'none'
        this.vars.isNewRepoSectionOpen = false
        this.elements.newRepo_addButton.textContent = 'Add repository'
        this.elements.newRepo_closeButton.style.display = 'none'
    }

    handleIsPrivateRepoInput(e) {
        if (e.target.checked) {
            this.elements.newRepo__accountSelectDiv.style.display = 'flex';
            this.elements.newRepo_accountSelect.update();
        } else if (!e.target.checked) {
            this.elements.newRepo__accountSelectDiv.style.display = 'none';
        }
    }

    async handleAddButton() {
        const vars = this.vars;
        const wrapper = this.elements.newRepo_wrapper;

        if (vars.isNewRepoSectionOpen && wrapper.style.display == 'none') {
            wrapper.style.display = 'none'
            vars.isNewRepoSectionOpen = false
        } else if (!vars.isNewRepoSectionOpen && wrapper.style.display == 'none') {
            this.elements.newRepo_addButton.textContent = 'Confirm ✓'
            reposList__closeRepoButton.style.display = 'block'
            vars.isNewRepoSectionOpen = true
            wrapper.style.display = 'flex'
        } else {
            const repo_url = this.elements.newRepo_urlInput.value;
            const branch = this.elements.newRepo_branchSelect.e.value;
            
            if (!repo_url || !branch) {
                this.elements.newRepo_errMsg.textContent = 'url and branch are required';
                return;
            }
    
            const match = repo_url.match(/github\.com\/([^\/]+)\/([^\/.]+)/);
            if (!match) {
                this.elements.newRepo_errMsg.textContent = 'url not valid';
                return;
            }

            const repoOwnerName = match[1];
            const repoName = match[2];
            const repoFullName = `${repoOwnerName}/${repoName}`;
            const replacedRepoName = repoFullName.replace("/", ".") + '.' + branch;

            let accountUsername = null;
            const pathToDockerfile = this.elements.newRepo_dockerfilepathInput.value;
            const dockerRootPath = pathToDockerfile[0] == '/' ? pathToDockerfile.slice(1) : pathToDockerfile;
            const isPrivateRepo = this.elements.newRepo_isPrivateRepoInput.checked;

            if (this.elements.newRepo_isPrivateRepoInput.checked) {
                accountUsername = this.elements.newRepo_accountSelect.e.value;
            }

            // добавление репозитория на сервере
            let account = '';
            let access_token = '';
            if (isPrivateRepo) {
                const accounts = await JSON.parse(window.localStorage.getItem('accounts'));
                account = accounts[accountUsername];
                access_token = account.access_token;
            }
            const privateRepoUrl = `https://${access_token}@github.com/${repoOwnerName}/${repoName}.git`;

            const repoData = {
                url: repo_url,                              // private/public
                privateUrl: privateRepoUrl,
                fullName: repoFullName,                     // String: owner/repoName
                ownerName: repoOwnerName,
                repoName: repoName,
                name: replacedRepoName,                     // String: owner.repoName.baranch
                branchName: branch,
                isPrivate: isPrivateRepo,                   // true/false
                account: {
                    username: isPrivateRepo == true ? account.username : '-',
                    name: isPrivateRepo == true ? account.name : '-',
                    access_token: isPrivateRepo == true ? access_token : '-',             // GitHub account`s access_token
                },
                git: {
                    isPulled: false,                        // true/false
                    commitHash: 1,
                },
                docker: {
                    imageName: replacedRepoName.toLowerCase(),
                    rootPath: dockerRootPath,               // path to Dockerfile directory,
                    buildCommand: `docker build -t ${replacedRepoName.toLowerCase()}:latest ${dockerRootPath} --no-cache`,
                    isBuilded: false,                       // true/false
                    containerStatus: 'offline',             // offline/running/paused
                    runCommand: `docker run --name ${replacedRepoName.toLowerCase()} -d -p 8080:80 ${replacedRepoName.toLowerCase()}:latest`,
                }
            }
            console.log(repoData);

            this.vars.repos[replacedRepoName] = repoData;
            const reposStr = JSON.stringify(this.vars.repos);
            window.localStorage.setItem('repos', reposStr);

            const params = new URLSearchParams({ repo: JSON.stringify(repoData) });
            const res = await fetch(`${SERVER_URL}/api/new-repo?${params.toString()}`, { method: 'GET' });
            const resData = await res.json();
            if (!res.ok) {
                terminal.addMsg(400, resData?.message)
                return;
            }
            terminal.addMsg(200, resData?.message)
            // -----------------------------------

            this.spawnRepo(repoData)
            wrapper.style.display = 'none'
            this.elements.newRepo_closeButton.style.display = 'none'
            vars.isNewRepoSectionOpen = false
            this.elements.newRepo_addButton.textContent = 'Add repository'
        }
    }
    
}

class AccountsSection {
    constructor(selector) {
        this.section = document.querySelector(selector)

        this.vars = {
            isNewBlockOpen: false,
            accounts: {}
        }

        this.elements = {
            accountsWrapper: this.accountsWrapperProxy(),
            addAccountWrapper: this.addAccountWrapperProxy(),
            addButton: this.section.querySelector('#accounts__addButton'),
            closeButton: this.section.querySelector('#accounts__closeButton'),
            errMsg: this.section.querySelector('.accounts__newWrapper__errMsg')
        }

        this.init();
    }

    init() {
        this.loadAccounts();
        this.elements.addAccountWrapper.hide();

        this.elements.addButton.addEventListener('click', () => this.addButton_onClick())
        this.elements.closeButton.addEventListener('click', () => this.elements.addAccountWrapper.hide())
    }

    // FUNCTIONS
    addAccountWrapperProxy() {
        const wrapper = this.section.querySelector('.accounts__newWrapper')
        return {
            e: wrapper,

            hide: () => {
                wrapper.style.display = 'none';
                this.vars.isNewBlockOpen = false;
                this.elements.closeButton.style.display = 'none';
                this.elements.addButton.textContent = 'Add account';
            },

            show: () => {
                wrapper.style.display = 'flex';
                this.vars.isNewBlockOpen = true;
                this.elements.closeButton.style.display = 'block';
                this.elements.addButton.textContent = 'Confirm ✓';
                this.elements.errMsg.textContent = '';
            }
        }
    }

    accountsWrapperProxy() {
        const wrapper = this.section.querySelector('.accounts__wrapper')

        return {
            e: wrapper,

            appendAccount: (accountObj) => {
                const blockId = Date.now();
                this.vars.accounts[accountObj.username] = accountObj;
                
                const accountsStr = JSON.stringify(this.vars.accounts);
                window.localStorage.setItem('accounts', accountsStr);

                wrapper.innerHTML += `
                    <div id="${blockId}" class="--basicSection__block" data-username="${accountObj.username}">
                        <h3>${accountObj.username}(${accountObj.name})</h3>
                        <span>access_token: ${accountObj.access_token}</span>
                        <br>
                        <button style="background-color: red;" data-id="${blockId}" onclick="delete_account(this)">Delete</button>
                    </div>
                    <br>
                `
            }
        }
    }

    async loadAccounts() {
        const res = await fetch(`${SERVER_URL}/api/get-accounts`, { method: 'GET' })
        const resData = await res.json();
        window.localStorage.setItem('accounts', '{}');
        if (!res.ok) {
            terminal.addMsg(400, resData?.message)
            return;
        }
        for (const key in resData) {
            if (!key) {
                return;
            }
            this.elements.accountsWrapper.appendAccount(resData[key]);
            this.vars.accounts[key] = resData[key]
        }
        const accountsStr = JSON.stringify(this.vars.accounts);
        window.localStorage.setItem('accounts', accountsStr);
        terminal.addMsg(200, 'accounts list loaded')
    }

    // EVENT LISTENERS
    async addButton_onClick() {
        const isOpen = this.vars.isNewBlockOpen;
        const displayState = this.elements.addAccountWrapper.e.style.display;
        if (!isOpen) {
            this.elements.addAccountWrapper.show();
        } else if (isOpen && displayState != 'none') {
            const username = this.elements.addAccountWrapper.e.querySelector('input[name="username"]').value;
            const access_token = this.elements.addAccountWrapper.e.querySelector('input[name="access_token"]').value;

            if (!access_token) {
                this.elements.errMsg.textContent = 'access_token and username are required'
                return;
            }

            const res = await (await fetch(`https://api.github.com/users/${username}`, {method: 'GET'})).json()
            if (res.status == 404) {
                this.elements.errMsg.textContent = 'user not found';
            } else {
                const account = {
                    username: username,
                    name: res.name,
                    access_token: access_token
                }

                const accountObj = {
                    account: JSON.stringify(account)
                }
                const params = new URLSearchParams(accountObj);
                fetch(`${SERVER_URL}/api/new-account?${params.toString()}`, { method: 'GET' })
                .then(async res => {
                    const resData = await res.json();
                    if (!res.ok) {
                        terminal.addMsg(400, resData.message)
                        return;
                    }
                    this.elements.accountsWrapper.appendAccount(account);
                    this.elements.addAccountWrapper.hide();
                    terminal.addMsg(200, resData.message)
                })
            }
        }
    }
}

class Terminal {
    constructor(selector) {
        this.section = document.querySelector(selector);

        this.vars = {
            isResizing: false
        }

        this.elements = {
            msgWrapper: this.section.querySelector('.terminal_messagesWrapper'),
            clearButton: this.section.querySelector('.terminal__clearButton'),
            resizer: this.section.querySelector('#terminal_resizer'),
        }

        this.resizeTerminal = this.resizeTerminal.bind(this);
        this.stopResizeTerminal = this.stopResizeTerminal.bind(this);

        this.init();
    }

    init() {
        this.elements.clearButton.addEventListener('click', () => this.handleClearButton());
        this.elements.resizer.addEventListener('mousedown', () => this.handleResizer());
    }

    // FUNCTIONS
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
    }

    resizeTerminal(e) {
        if (!this.vars.isResizing) return;

        const newHeight = window.innerHeight - e.clientY;
        this.section.style.height = `${newHeight}px`;
    }

    stopResizeTerminal() {
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
        this.vars.isResizing = true
        document.addEventListener('mousemove', this.resizeTerminal)
        document.addEventListener('mouseup', this.stopResizeTerminal)
    }
}

const terminal = new Terminal('.terminal');
const reposListSection = new ReposList('.reposList');
const accountsSection = new AccountsSection('.accounts');





