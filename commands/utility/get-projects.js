const { SlashCommandBuilder } = require('discord.js');
const dotenv = require('dotenv');
const path = require('path');
dotenv.config();
const SERVER_URL = process.env.serverURL;
const COMMAND_NAME = path.basename(__filename).replace('.js', '');

module.exports = {
    data: new SlashCommandBuilder()
        .setName(COMMAND_NAME)
        .setDescription('Displays list of your projects'),

    execute: async function (interaction) {
        const parseProjects = (projects) => {
            text = '';
            for (const key in projects) {
                const project = projects[key];
                text += `Project: \`${project.name}\`; branch: \`${project.branch}\`;\nhash: \`\`\`st\n${project.hash}\`\`\`\n`;
            }
            interaction.reply('**Your projects:**\n' + text);
        }

        const username = interaction.user.username;
        try {
            const res = await fetch(`${SERVER_URL}/api/user/${username}/get-projects`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            })
            if (!res.ok) return interaction.reply('Error: '+resData.message);

            const resData = await res.json();
            if (resData.message) return interaction.reply(resData.message);

            parseProjects(resData.projects);
        } catch (err) {
            return interaction.reply(`Fetching error: \`${err}\``);
        };
    }
};
