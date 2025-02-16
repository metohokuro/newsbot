import discord
from discord import app_commands
from discord.ext import commands
import asyncio

TOKEN = "とーくん"  # ここにBotのトークンを入力

intents = discord.Intents.default()
intents.members = True  # メンバー情報を取得するために必要
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"スラッシュコマンド同期: {len(synced)}個のコマンド")
    except Exception as e:
        print(f"エラー: {e}")

async def send_dm(member: discord.Member, embed: discord.Embed, queue: asyncio.Queue):
    """ メンバーにDMを送信し、結果をqueueに追加する（並列処理用） """
    if not member.bot:
        try:
            await member.send(embed=embed)
            await queue.put(("success", member))
        except discord.Forbidden:
            await queue.put(("fail", member))

@bot.tree.command(name="news", description="サーバーの全メンバーにニュースをDMで送信します（管理者限定）")
@app_commands.describe(title="ニュースのタイトル", description="ニュースの説明")
async def news(interaction: discord.Interaction, title: str, description: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ あなたはこのコマンドを実行する権限がありません。", ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("サーバー内でのみ使用可能です。", ephemeral=True)
        return

    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    embed.set_footer(text=f"送信元: {guild.name}")

    response_message = await interaction.response.send_message("⌛ ニュースの送信を開始しています...\n✅ 送信成功: 0人\n❌ 送信失敗: 0人", ephemeral=False)

    queue = asyncio.Queue()
    tasks = []

    for member in guild.members:
        tasks.append(send_dm(member, embed, queue))

    # 並列処理で全員にDMを送る（同時に50人程度を処理）
    CHUNK_SIZE = 50  # 一度に並列処理する数
    sent_count = 0
    failed_count = 0

    # 進捗表示用のタスク
    async def update_progress():
        nonlocal sent_count, failed_count
        while True:
            try:
                result, _ = await queue.get()
                if result == "success":
                    sent_count += 1
                else:
                    failed_count += 1
                if sent_count + failed_count == len(tasks):
                    break
                # await response_message.edit(content=f"⌛ ニュースの送信中...\n✅ 送信成功: {sent_count}人\n❌ 送信失敗: {failed_count}人")
            except:
                break

    progress_task = asyncio.create_task(update_progress())

    # 50人ずつ並列処理
    for i in range(0, len(tasks), CHUNK_SIZE):
        await asyncio.gather(*tasks[i:i + CHUNK_SIZE])

    await progress_task  # 進捗更新タスクを終了

    # 最終結果を表示
    await response_message.edit(content=f"✅ **ニュースの送信が完了しました！**\n✅ 送信成功: {sent_count}人\n❌ 送信失敗: {failed_count}人")

bot.run(TOKEN)
