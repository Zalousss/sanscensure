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
TOKEN = os.getenv("DISCORD_TOKEN")

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')
    for guild in bot.guilds:
        invite_tracker[guild.id] = await guild.invites()

@bot.command()
@commands.has_permissions(administrator=True)
async def inviteset(ctx, invites: int, role: discord.Role):
    invitations_needed[ctx.guild.id] = invites
    role_rewards[ctx.guild.id] = role
    await ctx.send(f"Le rôle {role.name} sera donné après {invites} invitations.")

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
        
        if needed and role and user_invitations[inviter.id] >= needed:
            member_role = guild.get_member(inviter.id)  # Récupérer l'objet Member
            if member_role and role not in member_role.roles:
                await member_role.add_roles(role)
                await member_role.send(f"Bravo, tu as accès maintenant au rôle {role.name} !")

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
