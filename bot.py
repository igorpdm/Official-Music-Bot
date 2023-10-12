import asyncio
import random
import time
import discord
import pytube.extract
from pytube import Playlist
import pytube
from discord.ext import commands
from youtubesearchpython import VideosSearch
import os
from music import music
import pickle

intents = discord.Intents.all()
intents.voice_states = True
intents.presences = True

bot = commands.AutoShardedBot(command_prefix='!', intents=intents)
TOKEN = "BOT TOKEN"
ARQUIVO_DADOS = "info_musicas.pkl"

music_cache = []
queue = []
voice_client = None
current_song = None
downloading_playlist = False


@bot.event
async def on_ready():
    global music_cache
    print(f"Logged in as {bot.user.name} successfully")
    try:
        # Verifica se o arquivo "info_musicas.pkl" existe
        if not os.path.exists(ARQUIVO_DADOS):
            # Se não existir ele é criado
            open(ARQUIVO_DADOS, "w").close()
            print(f"Foi criado o arquivo {ARQUIVO_DADOS}")
        else:
            try:
                # Carrega os dados do arquivo no vetor music_cache
                with open('info_musicas.pkl', 'rb') as file:
                    if os.path.getsize(ARQUIVO_DADOS) > 0:
                        music_cache = pickle.load(file)
                        print("Dados carregados com sucesso")
            except Exception as e:
                print("Erro ao tentar carregar as músicas para o cache")
                print(e)
    except Exception as e:
        print(e)


import pickle

def update_pkl_file():
    """
    Updates the music_cache dictionary in a pickle file.

    The function opens a file in binary write mode and dumps the music_cache dictionary
    into it using the pickle module. If the operation is successful, it prints a success
    message and returns. If an exception occurs, it prints an error message and the
    exception details.

    Args:
        None

    Returns:
        None
    """
    global music_cache
    try:
        with open(ARQUIVO_DADOS, 'wb') as file:
            pickle.dump(music_cache, file)
            print("info_musicas.pkl atualizado com sucesso")
            return
    except Exception as e:
        print("Erro ao atualizar arquivo pkl")
        print(e)


def already_downloaded(musica):
    """
    Checks if a given music file has already been downloaded and is in the music_cache.

    Args:
        musica (str): The name of the music file to check.

    Returns:
        If the music file is in the music_cache and has already been downloaded, returns the corresponding Song object.
        Otherwise, returns None.
    """
    is_downloaded = False
    is_in_cache = False
    song = None
    # Verifica se a música está na music_cache
    try:
        for musicas in music_cache:
            if musicas.audio_file == musica:
                is_in_cache = True
                song = musicas
                break
    except Exception as e:
        print("Erro ao verificar se está ma cache")
        print(e)

    try:
        if song:
            for files in os.listdir():
                if files.endswith(".mp3"):
                    if files == song.audio_file:
                        is_downloaded = True
                        break
                    else:
                        is_downloaded = False
    except Exception as e:
        print("Erro ao verificar se já foi baixada a música")
        print(e)

    if is_in_cache is True and is_downloaded is True:
        return song
    else:
        return None


def update_music_cache(musica):
    """
    Updates the music cache with the given music.

    Parameters:
    musica (str): The name of the music to be added to the cache.

    Returns:
    None
    """
    for musicas in music_cache:
        if musicas == musica:
            return

    music_cache.append(musica)
    print("Salvo na cache com sucesso")
    return


@bot.command(name="play")
async def play(ctx, *, musica):
    """
    This function plays a song in a voice channel.

    Parameters:
    ctx (discord.ext.commands.Context): The context of the command.
    musica (str): The name of the song or the URL of the video/playlist to be played.

    Returns:
    None
    """
    try:
        if not ctx.author.voice:
            embed = discord.Embed(title="Erro",
                                  description="Você precisa estar em um canal de voz para usar esse comando.",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        # Verifica se é um link de vídeo isolado
        if "v=" in musica and "list=" not in musica:
            await play_by_video(ctx, musica)
            return
        # Verifica se é um link de playlist
        elif 'list=' in musica:
            if downloading_playlist:
                embed = discord.Embed(title="Erro",description="Uma playlist já está sendo baixada\n Tente novamente "
                                                               "mais tarde", color=discord.Color.red())
                await ctx.reply(embed=embed)
                return
            await play_by_playlist(ctx, musica)
            return
        # Se cair no else significa que é um nome de música
        elif 'list=' not in musica and 'v=' not in musica:
            await play_by_name(ctx, musica)
            return
    except Exception as e:
        print("Erro na função play")
        print(e)


# Toca a próxima música quando a anterior acaba
async def play_next(ctx):
    """
    Plays the next song in the queue, if there is one. If the queue is empty, disconnects the voice client.
    """
    global voice_client, queue, current_song
    if len(queue) > 0:
        next_song = queue[0].audio_file
        current_song = queue[0].nome
        queue.pop(0)
        voice_client.play(discord.FFmpegPCMAudio(next_song),
                          after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
    else:
        await voice_client.disconnect()
        voice_client = None
        current_song = None


async def play_by_video(ctx, url_musica):
    """
    Plays a music from a given YouTube video URL.

    Args:
        ctx (discord.ext.commands.Context): The context of the command.
        url_musica (str): The URL of the YouTube video.

    Returns:
        None
    """
    global voice_client, queue, music_cache
    video_id = pytube.extract.video_id(url_musica) + ".mp3"
    await play_music(ctx, video_id, url_musica)


async def play_by_playlist(ctx, link_playlist):
    """
    Downloads and plays a playlist of music videos from YouTube.

    Args:
        ctx (discord.ext.commands.Context): The context of the command.
        link_playlist (str): The URL of the YouTube playlist to be played.

    Returns:
        None
    """
    global downloading_playlist
    downloading_playlist = True
    playlist = Playlist(link_playlist)
    first_music_id = pytube.extract.video_id(playlist[0]) + ".mp3"
    first_music_url = playlist[0]
    downloaded_musics = 0
    is_first_music = True
    embed = discord.Embed(title="Playlist", description="A sua playlist está sendo carregada.\n Aguarde")
    mensagem = await ctx.send(embed=embed)
    start = time.time()
    try:
        for musicas in playlist.video_urls:
            video_id = pytube.extract.video_id(musicas) + ".mp3"
            song = already_downloaded(video_id)
            if is_first_music:
                await play_music(ctx, video_id, musicas)
                is_first_music = False
            else:
                if song is not None:
                    queue.append(song)
                    downloaded_musics += 1
                else:
                    try:
                        musica = await download(musicas)
                        queue.append(musica)
                        downloaded_musics += 1
                        embed = discord.Embed(title="Playlist",
                                              description="A sua playlist está sendo carregada.\n Este processo pode demorar bastante")
                        embed.set_footer(text=f"Baixado {downloaded_musics} de {len(playlist)}")
                        await mensagem.edit(embed=embed)
                    except Exception as e:
                        print("Erro ao baixar as músicas da playlist")
                        print(e)
    except Exception as e:
        print(e)
    await mensagem.delete()
    end = time.time()
    print(f"Tempo necessário para baixar a playlist: {end - start}")
    downloading_playlist = False
    update_pkl_file()
    return


async def play_by_name(ctx, nome_musica):
    """
    Searches for a music video on YouTube based on the given name and plays it in the voice channel.
    
    Args:
    - ctx: The context of the command.
    - nome_musica: The name of the music to be searched on YouTube.
    """
    global voice_client, music_cache, queue
    try:
        results = VideosSearch(nome_musica, limit=1, region="BR").result()['result']
        video_id = results[0]['id'] + '.mp3'
        video_url = results[0]['link']
    except Exception as e:
        embed = discord.Embed(title="Erro",
                              description="Não foi encontrada nenhuma música com esse nome\n Verifique se o nome está "
                                          "correto e tente novamente",
                              color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await play_music(ctx, video_id, video_url)
    return


async def play_music(ctx, video_id, video_url):
    """
    Plays music in a voice channel.

    Args:
        ctx (discord.ext.commands.Context): The context of the command.
        video_id (str): The ID of the video to play.
        video_url (str): The URL of the video to play.

    Returns:
        None
    """
    global voice_client, music_cache, queue, current_song
    channel = ctx.message.author.voice.channel
    if voice_client is None:
        # Verifica se a música ja foi baixada alguma vez
        song = already_downloaded(video_id)
        if song is not None:
            embed = discord.Embed(title="Play", description=f"Tocando: {song.nome}", color=discord.Color.green())
            mensagem = await ctx.send(embed=embed)
            voice_client = await channel.connect()
            voice_client.play(discord.FFmpegPCMAudio(video_id),
                              after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            current_song = song.nome
            return
        else:
            embed = discord.Embed(title="Carregando", description=f"Sua música está sendo carregada",
                                  color=discord.Color.green())
            mensagem = await ctx.send(embed=embed)
            try:
                musica = await download(video_url)
                update_pkl_file()
                voice_client = await channel.connect()
                voice_client.play(discord.FFmpegPCMAudio(musica.audio_file),
                                  after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
                current_song = musica.nome
                embed = discord.Embed(title="Play", description=f"Tocando: {musica.nome}", color=discord.Color.green())
                await mensagem.edit(embed=embed)
                return
            except Exception as e:
                print(e)
    else:

        song = already_downloaded(video_id)
        if song is not None:
            queue.append(song)
            embed = discord.Embed(title="Fila", description=f"Adicionado a fila: {song.nome}",
                                  color=discord.Color.green())
            embed.set_footer(text=f"Posição da fila: {len(queue)}")
            mensagem = await ctx.send(embed=embed)
            return
        else:
            embed = discord.Embed(title="Carregando", description=f"Sua música está sendo carregada",
                                  color=discord.Color.green())
            mensagem = await ctx.send(embed=embed)
            musica = await download(video_url)
            update_pkl_file()
            queue.append(musica)
            embed = discord.Embed(title="Fila", description=f"Adicionado a fila: {musica.nome}",
                                  color=discord.Color.green())
            embed.set_footer(text=f"Posição da fila: {len(queue)}")
            await mensagem.edit(embed=embed)
            return


@bot.command(name="stop")
async def stop(ctx):
    """
    Stops the music playback and clears the queue.

    Parameters:
    ctx (discord.ext.commands.Context): The context of the command.

    Returns:
    None
    """
    global voice_client, queue
    try:
        if voice_client:
            await voice_client.disconnect()
            voice_client = None
            queue.clear()
            embed = discord.Embed(title="Stop", description="A reprodução da música foi interrompida",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        else:
            embed = discord.Embed(title="Stop", description="O bot não está tocando nenhuma música",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            return
    except Exception as e:
        print("erro ao tentar parar a musica")
        print(e)
        return


@bot.command("skip")
async def skip(ctx):
    """
    Skips the current song being played and plays the next song in the queue, if there is one.

    Parameters:
    - ctx (discord.ext.commands.Context): The context of the command.

    Returns:
    - None
    """
    global voice_client, queue
    try:
        if voice_client:
            if len(queue) > 0:
                voice_client.stop()
                embed = discord.Embed(title="Skip",
                                      description=f"Pulando para a próxima música da fila\n{queue[0].nome}",
                                      color=discord.Color.green())
                await ctx.send(embed=embed)
                return
            else:
                embed = discord.Embed(title="Skip", description="Não há musicas na fila",
                                      color=discord.Color.green())
                await ctx.send(embed=embed)
                return
        else:
            embed = discord.Embed(title="Skip", description="O bot não está reproduzindo nenhuma música",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            return
    except Exception as e:
        print("Erro ao tentar skippar a musica")
        print(e)


@bot.command(name="shuffle")
async def shuffle(ctx):
    global queue, voice_client
    try:
        if voice_client:
            if len(queue) > 0:
                random.shuffle(queue)
                embed = discord.Embed(title="Shuffle", description="Todas as músicas da fila foram misturadas",
                                      color=discord.Color.green())
                await ctx.send(embed=embed)
                return
            else:
                embed = discord.Embed(title="Shuffle", description="A fila está vazia",
                                      color=discord.Color.red())
                await ctx.send(embed=embed)
                return
        else:
            embed = discord.Embed(title="Erro", description="O bot não está tocando nenhuma música",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            return
    except Exception as e:
        print("Erro ao usar o comando shuffle")
        print(e)


@bot.command(name="pause")
async def pause(ctx):
    """
    Pauses the currently playing music.

    If there is no music playing, sends a message indicating that the bot is not playing any music.

    Returns:
        None
    """
    global voice_client
    try:
        if voice_client:
            voice_client.pause()
            embed = discord.Embed(title="Pause", description="Música pausada",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
            return
        else:
            embed = discord.Embed(title="Pause", description="O bot não está tocando música",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
            return
    except Exception as e:
        print("Erro ao pausar")
        print(e)


@bot.command(name="resume")
async def resume(ctx):
    """
    Resumes the playback of the current song if it was previously paused.

    If the bot is not currently playing any music, an error message will be displayed.

    If the bot is currently playing music but it is not paused, a message will be displayed indicating that the music is not paused.

    If the bot is currently playing music and it is paused, the music will be resumed and a message will be displayed indicating that the music has been resumed.
    """
    global voice_client
    try:
        if voice_client:
            if voice_client.is_paused():
                voice_client.resume()
                embed = discord.Embed(title="Resume", description="A reprodução da música foi retomada",
                                      color=discord.Color.green())
                await ctx.send(embed=embed)
                return
            else:
                embed = discord.Embed(title="Resume", description="A Música não está pausada",
                                      color=discord.Color.green())
                await ctx.send(embed=embed)
                return
        else:
            embed = discord.Embed(title="Resume", description="O bot não está tocando música",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
            return
    except Exception as e:
        print("erro ao retomar a música")
        print(e)


async def download(musica):
    """
    Downloads a YouTube video as an mp3 file and returns a music object.

    Args:
        musica (str): The URL of the YouTube video to download.

    Returns:
        music: A music object representing the downloaded mp3 file.

    Raises:
        Exception: If an error occurs while downloading the video.
    """
    try:
        video = pytube.YouTube(musica)
        audio_stream = video.streams.filter(only_audio=True).first()
        audio_file = f'{video.video_id}.mp3'
        audio_stream.download(filename=audio_file)
        musica = music(video.title, audio_file)
        update_music_cache(musica)
        return musica
    except Exception as e:
        print("erro ao baixar a musica")
        print(e)


async def search_music(ctx, nome_musica):
    """
    Searches for a music video on YouTube based on the given name.

    Args:
        ctx (discord.ext.commands.Context): The context of the command.
        nome_musica (str): The name of the music to search for.

    Returns:
        list: A list of dictionaries containing information about the search results.
              Each dictionary represents a single video.
    """
    try:
        results = VideosSearch(nome_musica, limit=1, region="BR").result()['result']
        return results
    except Exception as e:
        embed = discord.Embed(title="Erro",
                              description="Não foi encontrada nenhuma música com esse nome\n Verifique se o nome está "
                                          "correto e tente novamente",
                              color=discord.Color.red())
        await ctx.send(embed=embed)
        return


# @bot.command(name="download")
# async def download_music(ctx, *, musica):
#     # Verifica se é um link de vídeo isolado
#     if "v=" in musica and "list=" not in musica:
#         try:
#             video_id = pytube.extract.video_id(musica) + ".mp3"
#             song = already_downloaded(video_id)
#             if song:
#                 embed = discord.Embed(title="Baixando", description="Essa música já foi baixada",
#                                       color=discord.Color.green())
#                 mensagem = await ctx.send(embed=embed)
#                 return
#             else:
#                 embed = discord.Embed(title="Baixando", description="Sua música está sendo baixada",
#                                       color=discord.Color.green())
#                 mensagem = await ctx.send(embed=embed)
#                 start = time.time()
#                 await download(musica)
#                 update_pkl_file()
#                 end = time.time()
#                 embed = discord.Embed(title="Baixando", description="Sua música foi baixada com sucesso",
#                                       color=discord.Color.green())
#                 embed.set_footer(text=f"tempo necessário: {round(end - start)} segundos")
#                 await mensagem.edit(embed=embed)
#                 return
#         except Exception as e:
#             print("Erro ao baixar a música por vídeo")
#             print(e)
#     # Verifica se é um link de playlist
#     elif 'list=' in musica:
#         downloaded_musics = 0
#         playlist = Playlist(musica)
#         embed = discord.Embed(title="Baixando",
#                               description="Sua playlist está sendo baixada\n Esse processo pode ser bem demorado",
#                               color=discord.Color.green())
#         mensagem = await ctx.send(embed=embed)
#         start = time.time()
#         try:
#             for musicas in playlist:
#                 video_id = pytube.extract.video_id(musicas) + ".mp3"
#                 song = already_downloaded(video_id)
#                 if song:
#                     downloaded_musics += 1
#                 else:
#                     await download(musicas)
#                     downloaded_musics += 1
#                 embed = discord.Embed(title="Baixando",
#                                       description="Sua playlist está sendo baixada\n Esse processo pode ser bem demorado",
#                                       color=discord.Color.green())
#                 embed.set_footer(text=f"Baixado {downloaded_musics} de {len(playlist)}")
#                 await mensagem.edit(embed=embed)
#         except Exception as e:
#             print("erro ao baixar playlist")
#             print(e)
#         end = time.time()
#         embed = discord.Embed(title="Baixando", description="Sua playlist foi baixada com sucesso",
#                               color=discord.Color.green())
#         embed.set_footer(text=f"tempo necessário: {round(end - start)} segundos")
#         await mensagem.edit(embed=embed)
#         update_pkl_file()
#         return
#     # Se cair no else significa que é um nome de música
#     elif 'list=' not in musica and 'v=' not in musica:
#         nome_musica = ' '.join(musica)
#         try:
#             music = search_music(ctx, nome_musica)
#             video_id = music[0]['id'] + '.mp3'
#             video_url = music[0]['link']
#             song = already_downloaded(video_id)
#             if song:
#                 embed = discord.Embed(title="Baixando", description="Essa música já foi baixada",
#                                       color=discord.Color.green())
#                 mensagem = await ctx.send(embed=embed)
#                 return
#             else:
#                 embed = discord.Embed(title="Baixando", description="Sua música está sendo baixada",
#                                       color=discord.Color.green())
#                 mensagem = await ctx.send(embed=embed)
#                 start = time.time()
#                 await download(video_url)
#                 update_pkl_file()
#                 end = time.time()
#                 embed = discord.Embed(title="Baixando", description="Sua música foi baixada com sucesso",
#                                       color=discord.Color.green())
#                 embed.set_footer(text=f"tempo necessário: {round(end - start)} segundos")
#                 await mensagem.edit(embed=embed)
#                 return
#         except Exception as e:
#             print("Erro ao baixar pelo nome")
#             print(e)


@bot.command(name="nowplaying")
async def nowplaying(ctx):
    """
    Sends a message to the Discord channel with the current song that the bot is playing.

    Parameters:
    ctx (discord.ext.commands.Context): The context of the command.

    Returns:
    None
    """
    global current_song
    try:
        if current_song:
            embed = discord.Embed(title="Nowplaying", description=f"Música atual: {current_song}",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Nowplaying", description=f"O bot não está tocando nenhuma música",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
    except Exception as e:
        print("Earro ao mostrar a musica atual")
        print(e)


async def cria_lista(ctx, queue):
    """
    Creates a paginated list of songs in the queue.

    Args:
        ctx (discord.ext.commands.Context): The context of the command.
        queue (list): The list of songs in the queue.

    Returns:
        None
    """
    num_comandos_por_pagina = 10
    num_paginas = -(-len(queue) // num_comandos_por_pagina)  # ceil division
    pagina_atual = 1

    def cria_embed():
        """
        Creates an embed with the current page of songs in the queue.

        Args:
            None

        Returns:
            discord.Embed: The embed with the current page of songs in the queue.
        """
        primeira_musica = 1
        embed = discord.Embed(title="Fila")
        embed.set_footer(text=f"Página {pagina_atual} de {num_paginas}")
        for musica in queue[
                      (pagina_atual - 1)
                      * num_comandos_por_pagina: pagina_atual
                                                 * num_comandos_por_pagina
                      ]:
            embed.add_field(name=f"{queue.index(musica) + 1}ª:", value=musica.nome, inline=False)
            primeira_musica += 1
        return embed

    embed = cria_embed()
    mensagem = await ctx.reply(embed=embed)
    if num_paginas > 1:
        await mensagem.add_reaction("◀️")
        await mensagem.add_reaction("❌")
        await mensagem.add_reaction("▶️")

    def verifica_reacao(reaction, user):
        return (
                user == ctx.author
                and reaction.message == mensagem
                and reaction.emoji in ["◀️", "❌", "▶️"]
        )

    while True:
        try:
            reaction, user = await ctx.bot.wait_for(
                "reaction_add", timeout=120.0, check=verifica_reacao
            )
        except asyncio.TimeoutError:
            await mensagem.delete()
            await ctx.message.delete()
            break

        if reaction.emoji == "▶️" and pagina_atual < num_paginas:
            pagina_atual += 1
            embed = cria_embed()
            await mensagem.edit(embed=embed)
            await reaction.remove(user)

        elif reaction.emoji == "◀️" and pagina_atual > 1:
            pagina_atual -= 1
            embed = cria_embed()
            await mensagem.edit(embed=embed)
            await reaction.remove(user)
        elif reaction.emoji == "▶️" and pagina_atual == num_paginas:
            embed = cria_embed()
            await mensagem.edit(embed=embed)
            await reaction.remove(user)
        elif reaction.emoji == "◀️" and pagina_atual == 1:
            embed = cria_embed()
            await mensagem.edit(embed=embed)
            await reaction.remove(user)
        else:
            await mensagem.delete()
            await ctx.message.delete()


@bot.command(name="queue")
async def fila(ctx):
    """
    Sends a message to the Discord channel with the current queue of songs to be played.

    If the queue is empty, sends a message indicating that the queue is empty.
    If the queue is not empty, calls the function 'cria_lista' to create a list of songs and sends it to the channel.
    """
    global queue, voice_client
    try:
        if not queue:
            embed = discord.Embed(title="Fila", description=f"A fila está vazia",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            await cria_lista(ctx, queue=queue)
            return
    except Exception as e:
        print("Erro ao criar a lista")
        print(e)


@bot.command(name="remove")
async def remove(ctx, index):
    """
    Removes a song from the queue at the specified index.

    Parameters:
    - ctx (discord.ext.commands.Context): The context of the command.
    - index (int): The index of the song to be removed from the queue.

    Returns:
    - None
    """
    global queue,voice_client
    try:
        if not queue:
            embed = discord.Embed(title="Fila", description=f"A fila está vazia",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
        elif index >= len(queue):
            embed = discord.Embed(title="Fila", description=f"Posição da fila inválida",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            queue.pop(index-1)
            embed = discord.Embed(title="Fila", description=f"Música removida da fila com sucesso",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
    except Exception as e:
        print("Erro ao retirar a música da fila")
        print(e)




bot.run(TOKEN)