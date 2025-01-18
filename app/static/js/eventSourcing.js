
async function sseConnection(url, urlSerachParams) {
    const eventSource = new EventSource(`${SERVER_URL}${url}?${urlSerachParams.toString()}`);

    eventSource.onopen = function () {
        terminal.addMsgBlock(`Request to ${url}`);
    }

    eventSource.onmessage = function (event) {
        const parsedData = JSON.parse(event.data);

        if (parsedData.type == 'error') {
            terminal.addMsgToBlock(parsedData.msg);
        }

        if (parsedData.type == 'close') {
            eventSource.close();
        }
        if (parsedData.msg) terminal.addMsgToBlock(parsedData.msg);
        return;
    }

    eventSource.onerror = function (err) {
        console.log(err);
        eventSource.close();
        terminal.addMsgToBlock(`Error: ${ {...err} }`);
        terminal.closeMsgBlock();
    }
}
/*
async function sseLoadRepos() {
    const eventSource = new EventSource(`${SERVER_URL}/api/get-repos`);

    eventSource.onopen = () => {
        terminal.addMsgBlock('Updating repos');
    }

    eventSource.onmessage = (dataStr) => {
        const data = dataStr.json();
        if (data.status != 200) {
            return terminal.addMsgToBlock(`Load repo error: ${data.msg}`);
        }

        reposListSection.
    }

    eventSource.onerror = (err) => {
        terminal.addMsgToBlock(`Updating repos error: ${err}`);
        terminal.closeMsgBlock();
    }
}
*/














