import discord



from discord import app_commands, Embed, Color



from discord.ext import commands



import asyncio



import json



import os



import time



from gtts import gTTS



from datetime import datetime







# --- BOT YAPILANDIRMASI ---



class EkipBot(commands.Bot):



    def __init__(self):



        intents = discord.Intents.all()



        super().__init__(command_prefix="!", intents=intents)



        self.guard_file = "guard_list.json"



        self.stats_file = "voice_stats.json"



        self.guard_data = self.load_json(self.guard_file)



        self.total_stats = self.load_json(self.stats_file)



        self.active_sessions = {}







    def load_json(self, filename):



        if os.path.exists(filename):



            try:



                with open(filename, "r", encoding="utf-8") as f:



                    return json.load(f)



            except: return {}



        return {}







    def save_json(self, data, filename):



        with open(filename, "w", encoding="utf-8") as f:



            json.dump(data, f, indent=4, ensure_ascii=False)







    async def setup_hook(self):



        await self.tree.sync()



        print(f"✅ Sistem Aktif | Guard: {len(self.guard_data)}")







bot = EkipBot()







# --- YETKİ KONTROL ---



def has_permission(perm_name: str):



    async def predicate(interaction: discord.Interaction):



        uid = str(interaction.user.id)



        if interaction.user.id == interaction.guild.owner_id: return True



        if uid in bot.guard_data and (bot.guard_data[uid].get(perm_name) or bot.guard_data[uid].get("full")): return True



        await interaction.response.send_message(f"❌ **YETKİ YOK:** `{perm_name}` yetkiniz bulunmuyor!", ephemeral=True)



        return False



    return app_commands.check(predicate)







# --- 🕒 SES TAKİP ---



@bot.event



async def on_voice_state_update(member, before, after):



    user_id = str(member.id)



    if before.channel is None and after.channel is not None:



        bot.active_sessions[user_id] = time.time()



    elif before.channel is not None and after.channel is None:



        if user_id in bot.active_sessions:



            duration = time.time() - bot.active_sessions.pop(user_id)



            bot.total_stats[user_id] = bot.total_stats.get(user_id, 0) + duration



            bot.save_json(bot.total_stats, bot.stats_file)







# --- 📊 SES İSTATİSTİK ---



@bot.tree.command(name="sesistatistik", description="Detaylı ses verilerini ve ilk 5 sıralamasını gösterir.")



async def sesistatistik(interaction: discord.Interaction, üye: discord.Member = None):



    üye = üye or interaction.user



    uid = str(üye.id)



    total_seconds = bot.total_stats.get(uid, 0)



    current_session_text = "Şu an seste değil."



    if uid in bot.active_sessions:



        current_duration = int(time.time() - bot.active_sessions[uid])



        total_seconds += current_duration



        current_session_text = f"🔴 Aktif: {current_duration // 60} dk, {current_duration % 60} sn"



    h, m = divmod(int(total_seconds), 3600)



    m, s = divmod(m, 60)



    embed = Embed(title=f"🎙️ Ses Verileri: {üye.name}", color=Color.green())



    embed.add_field(name="⌛ Toplam Süre", value=f"**{h} saat, {m} dakika, {s} saniye**", inline=False)



    embed.add_field(name="📺 Mevcut Oturum", value=current_session_text, inline=True)



    if üye.voice:



        embed.add_field(name="📍 Kanal", value=üye.voice.channel.name, inline=True)



        embed.add_field(name="🎤 Durum", value="Mute" if üye.voice.self_mute else "Açık", inline=True)



    if bot.total_stats:



        temp_stats = bot.total_stats.copy()



        for active_uid, start_time in bot.active_sessions.items():



            temp_stats[active_uid] = temp_stats.get(active_uid, 0) + (time.time() - start_time)



        sorted_stats = sorted(temp_stats.items(), key=lambda x: x[1], reverse=True)[:5]



        ranking_text = ""



        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]



        for i, (user_id, total_time) in enumerate(sorted_stats):



            th, tm = divmod(int(total_time), 3600)



            ranking_text += f"{medals[i]} <@{user_id}> ➔ **{th}s {tm}dk**\n"



        embed.add_field(name="🏆 En Çok Vakit Geçiren İlk 5", value=ranking_text, inline=False)



    embed.set_thumbnail(url=üye.display_avatar.url)



    await interaction.response.send_message(embed=embed)







# --- 🚫 BAN SORGULAMA (YENİ) ---



@bot.tree.command(name="ban-sorgu", description="[MOD] Banlanmış bir kullanıcının ban sebebini sorgular.")



@has_permission("mod")



async def ban_sorgu(interaction: discord.Interaction, kullanici_id: str):



    try:



        ban_entry = await interaction.guild.fetch_ban(discord.Object(id=int(kullanici_id)))



        user = ban_entry.user



        reason = ban_entry.reason if ban_entry.reason else "Sebep belirtilmemiş."



        



        embed = Embed(title="🚫 Ban Sorgu Sonucu", color=Color.red())



        embed.add_field(name="Kullanıcı", value=f"{user.name}#{user.discriminator} ({user.id})", inline=False)



        embed.add_field(name="Ban Sebebi", value=f"```{reason}```", inline=False)



        embed.set_thumbnail(url=user.display_avatar.url if user.avatar else None)



        await interaction.response.send_message(embed=embed)



    except discord.NotFound:



        await interaction.response.send_message("❌ Bu ID'ye sahip bir ban kaydı bulunamadı.", ephemeral=True)



    except ValueError:



        await interaction.response.send_message("❌ Geçerli bir sayısal ID giriniz.", ephemeral=True)



    except Exception as e:



        await interaction.response.send_message(f"❌ Bir hata oluştu: {e}", ephemeral=True)







# --- 🛡️ GUARD ---



@bot.tree.command(name="guard-ekle")



@app_commands.checks.has_permissions(administrator=True)



@app_commands.choices(yetki=[



    app_commands.Choice(name="👑 Full Yetki", value="full"),



    app_commands.Choice(name="📝 Kayıt Yetkisi", value="kayit"),



    app_commands.Choice(name="🔨 Moderasyon Yetkisi", value="mod"),



    app_commands.Choice(name="💬 Sohbet/Ses Yetkisi", value="sohbet")



])



async def guard_ekle(interaction: discord.Interaction, üye: discord.Member, yetki: app_commands.Choice[str]):



    uid = str(üye.id)



    if uid not in bot.guard_data: bot.guard_data[uid] = {"full": False, "kayit": False, "mod": False, "sohbet": False}



    bot.guard_data[uid][yetki.value] = True



    bot.save_json(bot.guard_data, bot.guard_file)



    await interaction.response.send_message(f"✅ {üye.mention} artık `{yetki.name}` yetkisine sahip.")







@bot.tree.command(name="guard-çıkar")



@app_commands.checks.has_permissions(administrator=True)



async def guard_cikar(interaction: discord.Interaction, üye: discord.Member):



    uid = str(üye.id)



    if uid in bot.guard_data:



        del bot.guard_data[uid]



        bot.save_json(bot.guard_data, bot.guard_file)



        await interaction.response.send_message(f"🗑️ {üye.mention} silindi.")







@bot.tree.command(name="guard-liste")



async def guard_liste(interaction: discord.Interaction):



    if not bot.guard_data: return await interaction.response.send_message("🛡️ Liste boş.")



    liste = "".join([f"• <@{u}> ➔ **{[k for k,v in p.items() if v]}**\n" for u,p in bot.guard_data.items()])



    await interaction.response.send_message(embed=Embed(title="🛡️ Guard Listesi", description=liste, color=Color.gold()))







# --- 👤 PROFİL ---



@bot.tree.command(name="profil")



async def profil(interaction: discord.Interaction, üye: discord.Member = None):



    üye = üye or interaction.user



    embed = Embed(title=f"👤 Profil: {üye.name}", color=üye.color)



    embed.add_field(name="ID", value=üye.id, inline=False)



    embed.add_field(name="Hesap", value=üye.created_at.strftime("%d/%m/%Y"), inline=True)



    embed.add_field(name="Giriş", value=üye.joined_at.strftime("%d/%m/%Y"), inline=True)



    embed.set_thumbnail(url=üye.display_avatar.url)



    await interaction.response.send_message(embed=embed)







# --- 🧹 MODERASYON ---



@bot.tree.command(name="mesaj-sil")



@has_permission("mod")



async def sil(interaction: discord.Interaction, miktar: int):



    await interaction.response.defer(ephemeral=True)



    deleted = await interaction.channel.purge(limit=miktar)



    await interaction.followup.send(f"✅ **{len(deleted)}** mesaj silindi.", ephemeral=True)







# --- 📝 KAYIT ---



@bot.tree.command(name="kayıt")



@has_permission("kayit")



async def kayit(interaction: discord.Interaction, üye: discord.Member, isim: str, yas: int):



    try:



        await üye.edit(nick=f"{isim} | {yas}")



        await interaction.response.send_message(f"✅ {üye.mention} kayıt edildi.")



    except: await interaction.response.send_message("❌ Yetki yetersiz!")







# --- 🔊 SESGEL ---



@bot.tree.command(name="sesegel")



@has_permission("sohbet")



async def sesegel(interaction: discord.Interaction):



    if not interaction.user.voice: return await interaction.response.send_message("❌ Sese gir!", ephemeral=True)



    await interaction.response.send_message("🎤 Geliyorum...", ephemeral=True)



    try:



        vc = await interaction.user.voice.channel.connect()



        gTTS(text="Cümbür cemaat merhabalar", lang='tr').save("selam.mp3")



        vc.play(discord.FFmpegPCMAudio('selam.mp3'))



        while vc.is_playing(): await asyncio.sleep(1)



        await vc.disconnect()



        if os.path.exists("selam.mp3"): os.remove("selam.mp3")



    except: 



        if interaction.guild.voice_client: await interaction.guild.voice_client.disconnect()







# --- 💬 SÖYLE ---



@bot.tree.command(name="söyle")



@has_permission("mod")



async def soyle(interaction: discord.Interaction, mesaj: str):



    await interaction.channel.send(mesaj)



    await interaction.response.send_message("Mesaj iletildi.", ephemeral=True)







# --- 🔍 GENEL SORGU KOMUTU (ID İLE) ---

@bot.tree.command(name="sorgu", description="ID girilen kullanıcının global Discord bilgilerini getirir.")

async def sorgu(interaction: discord.Interaction, kullanici_id: str):

    await interaction.response.defer() # Bilgi çekmek zaman alabilir, botu beklemeye alıyoruz

    try:

        # Kullanıcıyı ID ile Discord API'den çekiyoruz (Sunucuda olmasına gerek yok)

        user = await bot.fetch_user(int(kullanici_id))

        

        embed = Embed(title="🔍 Kullanıcı Sorgu Sonucu", color=Color.blue())

        embed.add_field(name="👤 Adı / Global Adı", value=f"{user.name}", inline=True)

        embed.add_field(name="🆔 Kullanıcı ID", value=f"{user.id}", inline=True)

        

        # Hesap açılış tarihini düzgün formatta yazalım

        tarih = user.created_at.strftime("%d/%m/%Y %H:%M")

        embed.add_field(name="📅 Hesap Açılış Tarihi", value=tarih, inline=False)

        

        # Profil Fotoğrafı

        if user.avatar:

            embed.set_thumbnail(url=user.avatar.url)

            embed.add_field(name="🖼️ Profil Fotoğrafı", value=f"[Resim Linki]({user.avatar.url})", inline=False)

        else:

            embed.add_field(name="🖼️ Profil Fotoğrafı", value="Varsayılan Avatar", inline=False)



        await interaction.followup.send(embed=embed)

        

    except discord.NotFound:

        await interaction.followup.send("❌ Bu ID'ye sahip bir kullanıcı Discord üzerinde bulunamadı.")

    except ValueError:

        await interaction.followup.send("❌ Lütfen sadece sayısal bir ID girin.")

    except Exception as e:

        await interaction.followup.send(f"❌ Bir hata oluştu: {e}")







class CekilisBot(commands.Bot):

    def __init__(self):

        intents = discord.Intents.all()

        super().__init__(command_prefix="!", intents=intents)

        # Ana botunla aynı guard dosyasını okuması için:

        self.guard_file = "guard_list.json"

        self.guard_data = self.load_guards()



    def load_guards(self):

        if os.path.exists(self.guard_file):

            try:

                with open(self.guard_file, "r") as f:

                    return json.load(f)

            except: return {}

        return {}



    async def setup_hook(self):

        await self.tree.sync()

        print("🎉 Yetki Kontrollü Çekiliş Sistemi Aktif!")



bot = CekilisBot()# --- 🛡️ YETKİ KONTROL FONKSİYONU ---def has_permission(perm_name: str):

async def predicate(interaction: discord.Interaction):

        uid = str(interaction.user.id)

        # Sunucu sahibi her zaman yetkilidir

        if interaction.user.id == interaction.guild.owner_id:

            return True

        # Guard listesinde yetkisi var mı kontrol et

        if uid in bot.guard_data:

            user_perms = bot.guard_data[uid]

            if user_perms.get(perm_name) or user_perms.get("full"):

                return True

        await interaction.response.send_message(f"❌ **YETKİ YOK:** Çekiliş yönetmek için `{perm_name}` veya `full` yetkiniz olmalı!", ephemeral=True)

        return False

    return app_commands.check(predicate)# --- 🎉 ÇEKİLİŞ BAŞLAT ---@bot.tree.command(name="çekiliş-yap", description="Yeni bir çekiliş başlatır.")@has_permission("mod") # Sadece moderasyon veya full yetkisi olanlarasync def cekilis_yap(interaction: discord.Interaction, odul: str):

    embed = Embed(

        title="🎁 DEV ÇEKİLİŞ BAŞLADI!",

        description=f"Ödül: **{odul}**\n\nKatılmak için aşağıdaki 🎉 tepkisine tıklayın!",

        color=Color.gold()

    )

    embed.set_footer(text="Çekilişi bitirmek için /çekiliş-sonuç komutunu kullanın.")

    

    await interaction.response.send_message(embed=embed)

    mesaj = await interaction.original_response()

    await mesaj.add_reaction("🎉")# --- 🏆 ÇEKİLİŞ BİTİR VE KAZANAN SEÇ ---@bot.tree.command(name="çekiliş-sonuç", description="Çekilişi bitirir ve kazananı ilan eder.")@has_permission("mod")async def cekilis_sonuc(interaction: discord.Interaction, mesaj_id: str):

    await interaction.response.defer()

    

    try:

        # Komutun yazıldığı kanaldaki mesajı bulur

        mesaj = await interaction.channel.fetch_message(int(mesaj_id))

        

        # 🎉 tepkisine tıklayanları çekelim

        reaction = discord.utils.get(mesaj.reactions, emoji="🎉")

        users = [user async for user in reaction.users() if not user.bot]

        

        if len(users) == 0:

            return await interaction.followup.send("❌ Çekilişe kimse katılmamış, kazanan yok!")



        kazanan = random.choice(users)

        

        embed = Embed(

            title="🎊 ÇEKİLİŞ SONUÇLANDI! 🎊",

            description=f"Tebrikler {kazanan.mention}, çekilişi kazandın!",

            color=Color.green()

        )

        embed.add_field(name="🏆 Kazanan", value=f"{kazanan.name}", inline=False)

        embed.set_image(url="https://media.giphy.com/media/26tOZ42Mg6pbTUPHW/giphy.gif")

        

        await interaction.followup.send(content=f"🔔 {kazanan.mention} kazandı!", embed=embed)

        

    except Exception as e:

        await interaction.followup.send(f"❌ Hata: Mesaj ID'sini yanlış girdin veya 🎉 tepkisi yok. (Hata: {e})") 



Abicim, isteğin üzerine sadece Moderasyon (mod) veya Full yetkisi olan guardların kullanabileceği, tamamen bağımsız bir DM Gönder botu hazırladım.

Bu bot da diğerleri gibi senin guard_list.json dosyanı okur, böylece yetki karmaşası yaşamazsın. /dm-gönder yazdığında bot senden bir kullanıcı ve mesaj isteyecek, sonra gidip o kişinin özel mesaj kutusuna (DM) senin mesajını iletecek.

İşte ayrı dosya olarak kullanabileceğin kod:

Python
import discord
from discord import app_commands, Embed, Color
from discord.ext import commands
import json
import os

class DMBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        # Ana botunla aynı guard dosyasını okur
        self.guard_file = "guard_list.json"

    def load_guards(self):
        if os.path.exists(self.guard_file):
            try:
                with open(self.guard_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return {}
        return {}

    async def setup_hook(self):
        await self.tree.sync()
        print("📩 DM Gönderim Sistemi Aktif!")

bot = DMBot()

# --- 🛡️ YETKİ KONTROL FONKSİYONU ---
def has_permission(perm_name: str):
    async def predicate(interaction: discord.Interaction):
        # Her seferinde güncel listeyi oku
        guard_data = bot.load_guards()
        uid = str(interaction.user.id)
        
        # Sunucu sahibi muaf
        if interaction.user.id == interaction.guild.owner_id:
            return True
            
        # Guard kontrolü
        if uid in guard_data:
            user_perms = guard_data[uid]
            if user_perms.get(perm_name) or user_perms.get("full"):
                return True
        
        await interaction.response.send_message(f"❌ **YETKİ YOK:** Bu komut için `{perm_name}` yetkiniz olmalı!", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- 📩 DM GÖNDER KOMUTU ---
@bot.tree.command(name="dm-gönder", description="[MOD] Belirtilen kullanıcıya bot üzerinden DM gönderir.")
@has_permission("mod")
async def dm_gonder(interaction: discord.Interaction, üye: discord.Member, mesaj: str):
    await interaction.response.defer(ephemeral=True) # İşlem uzun sürebilir
    
    try:
        # Şık bir embed ile gönderelim
        embed = Embed(
            title="📥 Yeni Bir Mesajın Var!",
            description=mesaj,
            color=Color.blue()
        )
        embed.set_footer(text=f"Gönderen Sunucu: {interaction.guild.name}")
        
        await üye.send(embed=embed)
        await interaction.followup.send(f"✅ Mesaj başarıyla {üye.mention} kullanıcısına iletildi.", ephemeral=True)
        
    except discord.Forbidden:
        await interaction.followup.send(f"❌ {üye.mention} kullanıcısının DM'leri kapalı olduğu için mesaj gönderilemedi.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Mesaj gönderilirken bir hata oluştu: {e}", ephemeral=True)






bot.run('MTQ5MDQzODc5NzE1MzAxMzg2MQ.GSCVFa.SNgpT0wyq_upMtOtGVAKau_ICdVM7msjwAR3mI')
