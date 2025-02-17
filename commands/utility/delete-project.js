const { ActionRowBuilder, SlashCommandBuilder, Events, ModalBuilder, TextInputBuilder, TextInputStyle } = require('discord.js');
const dotenv = require('dotenv');
const path = require('path');
dotenv.config();
const SERVER_URL = process.env.serverURL;
const COMMAND_NAME = path.basename(__filename).replace('.js', '');

module.exports = {
    data: new SlashCommandBuilder()
        .setName(COMMAND_NAME)
        .setDescription('Deletes a repository by hash')
        .addStringOption(option =>
			option
            .setName('hash')
            .setDescription('Hash of repository to delete')
            .setRequired(true)
        ),

    execute: async (interaction) => {
        const repoHash = interaction.options.getString('hash');
        const username = interaction.user.username;

        try {
            const res = await fetch(`${SERVER_URL}/api/user/${username}/project/${repoHash}/delete`, { method: 'DELETE' });
            const resData = await res.json();
            return interaction.reply({ content: resData.message });
        } catch (err) {
            return interaction.reply({ content: 'Fetching error: `'+err+'`' });
        }
    }
};
