const { ActionRowBuilder, SlashCommandBuilder, ModalBuilder, TextInputBuilder, TextInputStyle } = require('discord.js');
const dotenv = require('dotenv');
const path = require('path');
const EventSource = require('eventsource').EventSource;
dotenv.config();
const SERVER_URL = process.env.serverURL;
const COMMAND_NAME = path.basename(__filename).replace('.js', '');

module.exports = {
    data: new SlashCommandBuilder()
        .setName(COMMAND_NAME)
        .setDescription('Creating, downloading, building, running in docker and tunneling **your GitHub repository**'),

    execute: async (interaction) => {
        const modal = new ModalBuilder()
			.setCustomId(COMMAND_NAME)
			.setTitle('Your project`s settings');

		const repoUrl = new TextInputBuilder()
            .setValue('https://github.com/Tsyhanok-Ivan/world-of-go.git')
			.setCustomId('repoUrl')
			.setLabel('url of Git-Hub repository')
            .setPlaceholder('https://github.com/user/repo')
            .setRequired(true)
			.setStyle(TextInputStyle.Short);

		const githubToken = new TextInputBuilder()
            // .setValue('')
			.setCustomId('githubToken')
			.setLabel('Your GitHub access token')
            .setPlaceholder('Paste your GitHub token here')
            .setRequired(true)
			.setStyle(TextInputStyle.Short);

        const branchName = new TextInputBuilder()
            .setValue('render-server')
            .setCustomId('branchName')
            .setLabel('Branch name of GitHub repository.')
            .setPlaceholder('Default: main')
            .setRequired(false)
            .setStyle(TextInputStyle.Short);

        const ports = new TextInputBuilder()
            .setValue('3001/3001')
            .setCustomId('ports')
            .setLabel('App ports:')
            .setPlaceholder('pc-port/docker-port | Example: (3000/3000)')
            .setRequired(true)
            .setStyle(TextInputStyle.Short);

		modal.addComponents(
            new ActionRowBuilder().addComponents(repoUrl),
            new ActionRowBuilder().addComponents(githubToken),
            new ActionRowBuilder().addComponents(branchName),
            new ActionRowBuilder().addComponents(ports)
        );

		await interaction.showModal(modal);
    },

    onSubmitModal: async (interaction) => {
        let replyContent = 'Form processing...'
        const updateReply = (msg) => { interaction.editReply({ content: replyContent += `\n${msg}` }) };
        await interaction.reply({ content: replyContent, fetchReply: true })

        const username = interaction.user.username;
        const repoUrl = interaction.fields.getTextInputValue('repoUrl');
        const githubToken = interaction.fields.getTextInputValue('githubToken');
        const branchName = interaction.fields.getTextInputValue('branchName');
        const portsStr = interaction.fields.getTextInputValue('ports');

        // Ports validation
        const portRegex = /^(\d{1,5})\/(\d{1,5})$/;
        const match = portsStr.match(portRegex);

        if (!match) {
            return interaction.reply('Error: Please enter ports in the format "3001/3001".');
        }
        const ports = [parseInt(match[1], 10), parseInt(match[2], 10)];
        if (ports.some(port => port < 1 || port > 65535)) {
            return interaction.reply('Error: Ports must be in the range 1-65535.');
        }
        
        const data = {
            user: interaction.user,
            repo: {
                url: repoUrl,
                access_token: githubToken,
                branch: branchName,
                ports
            }
        }
        
        updateReply('Fetching.. (creating repository)');

        const res = await fetch(`${SERVER_URL}/api/user/${username}/project/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).catch(err => updateReply('Fetching error: `'+err+'`'));
        if (!res) return;

        const resData = await res.json();
        if (!res.ok) return updateReply(`Fatal error: ${resData.message}`);
        updateReply('Repository created');
        updateReply('Connecting to EventSource stream');

        const eventSource = new EventSource(`${SERVER_URL}/api/user/${username}/project/${resData.hash}/launch`);

        eventSource.addEventListener('open', () => {
            updateReply('Connected to EventSource stream');
        })

        eventSource.addEventListener('error', (err) => {
            return updateReply('EventSource error: '+err)
        })

        eventSource.addEventListener('message', (event) => {
            const data = JSON.parse(event.data);
            if (data.type == 'close') {
                eventSource.close();
                if (data.msg) return updateReply(data.msg);
            } else if (data.type == 'fatal') {
                updateReply('FATAL-ERROR - '+data.msg);
            } else if (data.type == 'info') {
                updateReply('INFO - '+data.msg);
            }

            if (data.close) return eventSource.close();
        })
    }
};
