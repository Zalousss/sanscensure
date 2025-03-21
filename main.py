import os
import discord
from discord.ext import commands
from collections import defaultdict
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Permet de lire les messages

bot = commands.Bot(command_prefix='+', intents=intents)

invite_tracker = {}
invitations_needed = {}  # Stocke le nombre d'invitations requises par serveur
role_rewards = {}  # Stocke le rôle à donner par serveur
user_invitations = defaultdict(int)  # Stocke le nombre d'invitations par utilisateur
log_channels = {}  # Stocke le salon où envoyer les logs
TOKEN = os.getenv("DISCORD_TOKEN")

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')
    for guild in bot.guilds:
        invite_tracker[guild.id] = await guild.invites()

@bot.command()
@commands.has_permissions(administrator=True)
async def inviteset(ctx, invites: int, role: discord.Role, log_channel: discord.TextChannel):
    invitations_needed[ctx.guild.id] = invites
    role_rewards[ctx.guild.id] = role
    log_channels[ctx.guild.id] = log_channel.id
    await ctx.send(f"Le rôle {role.name} sera donné après {invites} invitations. Logs envoyés dans {log_channel.mention}.")

@bot.event
async def on_member_join(member):
    guild = member.guild
    new_invites = await guild.invites()
    old_invites = invite_tracker.get(guild.id, [])
    
    inviter = None
    for invite in new_invites:
        for old_invite in old_invites:
            if invite.code == old_invite.code and invite.uses > old_invite.uses:
                inviter = invite.inviter
                break
        if inviter:
            break
    
    invite_tracker[guild.id] = new_invites
    
    if inviter and inviter != member:
        user_invitations[inviter.id] += 1
        needed = invitations_needed.get(guild.id)
        role = role_rewards.get(guild.id)
        log_channel_id = log_channels.get(guild.id)
        
        log_message = f"{inviter.mention} a invité {member.mention} et a maintenant {user_invitations[inviter.id]} invitations."
        if needed:
            remaining = max(0, needed - user_invitations[inviter.id])
            log_message += f" Il lui en reste {remaining} avant d'obtenir le rôle."
        
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(log_message)
        
        if needed and role and user_invitations[inviter.id] >= needed:
            inviter_member = await guild.fetch_member(inviter.id)  # Correction ici
            if inviter_member and role not in inviter_member.roles:
                await inviter_member.add_roles(role)
                await inviter_member.send(f"Bravo, tu as accès maintenant au rôle {role.name} !")

media_only_channels = set()

@bot.command()
@commands.has_permissions(administrator=True)
async def media(ctx, action: str, channel_id: int):
    if action == 'a':
        media_only_channels.add(channel_id)
        await ctx.send(f"Le salon <#{channel_id}> est maintenant en mode média uniquement.")
    elif action == 'd':
        media_only_channels.discard(channel_id)
        await ctx.send(f"Le mode média a été désactivé pour le salon <#{channel_id}>.")

@bot.event
async def on_message(message):
    if message.channel.id in media_only_channels and not message.attachments:
        await message.delete()
    await bot.process_commands(message)

# ---- Serveur Flask pour Render ----
app = Flask(__name__)

@app.route("/")
def home():
    return "Le bot est en ligne !", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))  # Render assigne automatiquement un port
    app.run(host="0.0.0.0", port=port)

# Lancer Flask et le bot en même temps
if __name__ == "__main__":
    Thread(target=run_flask).start()  # Lancer Flask en arrière-plan
    bot.run(TOKEN)
