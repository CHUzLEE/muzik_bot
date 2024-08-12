from audioop import reverse
from curses.ascii import islower
import discord
from discord.ext import commands
import random
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json

#from youtube_dl import YoutubeDL

#TODO ha elmegy a net folytassa, 
#   queue szamozas



class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
        #all the music related stuff
        self.is_playing = False
        self.is_paused = False
        self.first = ''
        self.isLooped = False
        

        # 2d array containing [song, Voicechannel]
        self.music_queue = []
        
        #this is the audio player's parameters
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        
        #this are the parameters to extract the youtube video informations
        self.YDL_OPTIONS = {'format': 'bestaudio/best','extract_flat': True, 'ignoreerrors': True, 'skip_unavailable_fragments': True, 'quiet': False}
        #self.YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist':True, 'skip_unavailable_fragments': True, 'extract_flat': True}
        
        #initialize spotify
        with open("spotify_token.txt", "r") as file:
            client_id = file.readline().rstrip('\n')
            client_secret = file.readline()
            client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)

        self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

        #voice channel info
        self.vc = None
        #temp list to append to queue (contains: source: URL/'spotify',  artist_name,  song_name )
        self.playlist_list = []
    #search playlist
    def search_play(self, item):
        self.playlist_list = []
        with  yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:  
            try:
                if 'spotify' in item:
                    if 'playlist' in item:
                        playlist = self.sp.playlist_tracks(item)
                        for track in playlist['items']:
                            track_name = track["track"]["name"]
                            artist_name = track["track"]["artists"][0]['name']
                            self.playlist_list.append({ 'source': "Spotify", 'title': track_name, 'channel': artist_name })
                    elif 'album' in item: 
                        playlist = self.sp.album_tracks(item)
                        for track in playlist['items']:
                            track_name = track["name"]
                            artist_name = track["artists"][0]['name']
                            self.playlist_list.append({ 'source': "Spotify", 'title': track_name, 'channel': artist_name })
                    else:
                        track_info = self.sp.track(track_id=item)
                        artist_name = track_info['artists'][0]['name']
                        song_name = track_info['name']
                        self.playlist_list.append({ 'source': "Spotify", 'title': track_name, 'channel': artist_name })
                        # item = artist_name + " " + song_name
                        # info = ydl.extract_info ("ytsearch:  %s" % item, download=False) 
                elif 'soundcloud' in item:
                    info = ydl.extract_info (item, download=False)
                    if '_type' in info: 
                    # if 'playlist' in info['_type']:
                        for tracks in info['entries']:
                            URL = tracks['url'].split('/')
                            track_name = URL[-1]
                            artist_name = URL[-2]
                            self.playlist_list.append({ 'source': tracks['url'], 'title': track_name, 'channel': artist_name})
                    else:
                        self.playlist_list.append({ 'source': info['original_url'], 'title': info['title'], 'channel': info['uploader']})
                else:
                #check if its a playlist, and we only extraxt the videos info (its faster)
                    if 'list=' in item:
                        #"ytsearch:  %s" % 
                        info = ydl.extract_info(item, download=False)['entries']
                        for videos in info:
                            if videos != None and videos['channel'] != None:
                                self.playlist_list.append({ 'source': videos['url'], 'title': videos['title'], 'channel': videos['channel']})
                   #elif '/watch' in item:
                   #    info = ydl.extract_info(item, download=False)
                    else:
                        #"ytsearch:  %s" %
                        info = ydl.extract_info (item, download=False)
                        self.playlist_list.append({ 'source': item, 'title': info['title'], 'channel': info['channel'] })
                    #TODO lehessen link nelkul keresni
                return self.playlist_list
            except Exception: 
                print("Hiba:  search_play url extract")
                return False             
        

    def play_next(self):
        if len(self.music_queue) > 0 :
            self.is_playing = True
            #get the first url
            m_url = self.music_queue[0][0]
            self.first = self.music_queue[0][0]['title'] + ' -> Uploader: ' + self.music_queue[0][0]['channel']
            #remove the first element as you are currently playing it
            if self.isLooped:
                self.music_queue.append(self.music_queue.pop(0))
            else:
                self.music_queue.pop(0)
            with  yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                try:
                    if 'Spotify' in m_url['source']:
                        info =  ydl.extract_info ("ytsearch:  %s" % (m_url['title'] + " - " + m_url['channel']), download=False)
                        info = ydl.extract_info (info['entries'][0]['url'], download=False)
                    else:
                        info =  ydl.extract_info (m_url['source'], download=False)
                except Exception: 
                    print("Hiba:  play_next() method  url extract")
            if info  == None:
                self.play_next()
            else:
                self.vc.play(discord.FFmpegOpusAudio(info['url'], **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_playing = False
            self.first = ""

    # infinite loop checking 
    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True

            m_url = self.music_queue[0][0]
            
            #try to connect to voice channel if you are not already connected
            if self.vc == None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()

                #in case we fail to connect
                if self.vc == None:
                    await ctx.send("Could not connect to the voice channel")
                    return
            else:
                await self.vc.move_to(self.music_queue[0][1])
            
            #remove the first element as you are currently playing it    
            self.first = self.music_queue[0][0]['title'] + ' -> Uploader: ' + self.music_queue[0][0]['channel'] #this line is only used for displaying the 1st song when ;queue command called
           
            if self.isLooped: #this section is to loop the playlist when looping is enabled
                self.music_queue.append(self.music_queue.pop(0))
            else:
                self.music_queue.pop(0)
                

            with  yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                try: 
                    if 'Spotify' in m_url['source']:
                        info =  ydl.extract_info ("ytsearch:  %s" % (m_url['title'] + " - " + m_url['channel']), download=False)
                        info = ydl.extract_info (info['entries'][0]['url'], download=False)
                    else:
                        info =  ydl.extract_info(m_url['source'], download=False)
                except Exception: 
                    print("Hiba:  play_music() method  url extract")
            if info == None:
                self.play_next()
            else:
                self.vc.play(discord.FFmpegOpusAudio(info['url'], **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_playing = False
            self.first = ""
    
    @commands.command(name="play", aliases=["p","playing"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        if ctx.author.voice is None:
            #you need to be connected so that the bot knows where to go
            await ctx.send("Cant add song, first connect to a voice channel!")
            return
        elif len(args) == 0:
            if self.is_paused:
                self.vc.resume()
        else: 
            song = self.search_play(args[0])
            if type(song) == type(True):
                await ctx.send("Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.")
            else:
                voice_channel = ctx.author.voice.channel
                if(len(args) >= 2):
                    try:
                        for s in reversed(song):
                            self.music_queue.insert(int(args[-1]),[s, voice_channel])
                    except:
                        print("error in adding song to a specific place in queue")
                else:
                    for s in song:
                        self.music_queue.append([s, voice_channel])
                
                if self.is_playing == False:
                    await self.play_music(ctx)
                await ctx.send("Song(s) added to the queue")

    @commands.command(name="pause",  aliases=["stop"], help="Pauses the current song being played")
    async def pause(self, ctx):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
            await ctx.send("Pausing")
        elif self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            await ctx.send("resuming")

    @commands.command(name = "resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx):
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            await ctx.send("resuming")

    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        if self.vc != None and self.vc:
            self.vc.stop()
            await ctx.send("Skipped a shitty music")


    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        retval = ''
        if self.first == "":
            retval += str(len(self.music_queue)) + " songs in queue\n"
        else:
            retval += str(len(self.music_queue) + 1) + " songs in queue\n"
        if self.first != '':
            retval += self.first + "\n"

        for i in range(0, len(self.music_queue)):
            # display a max of 5 songs in the current queue
            if (i > 9): break
            retval += self.music_queue[i][0]['title'] + ' -> Uploader: ' +self.music_queue[i][0]['channel']+  "\n"
        if retval != '':
            await ctx.send(retval)
        else:
            await ctx.send("No music in queue")

    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        self.music_queue = []
        self.first = ""
        self.is_paused = False
        self.is_playing = False
        if self.vc != None:
            self.vc.stop()
        await ctx.send("Music queue cleared")

    @commands.command(name="leave", aliases=["disconnect", "l", "d", "dc", "quit"], help="Kick the bot from VC")
    async def dc(self, ctx):
        self.is_playing = False
        self.is_paused = False
        if self.vc != None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        self.first = ""
        await ctx.send("Adios")
        await self.vc.disconnect()

    @commands.command(name="shuffle", aliases=["rnd", 'mix'], help="Shuffle the mix")
    async def shuffle(self, ctx):
        random.shuffle(self.music_queue)
        await ctx.send("Mix mixed")
    

    @commands.command(name="loop", aliases=["lp"], help="Looping the queue")
    async def loop(self, ctx):
        if self.isLooped == False:
            #puts the currently playing song to loop as well
            if self.first != "":
                self.music_queue.append(self.first)
            self.isLooped = True
            await ctx.send("Loop on")
        else:
            self.isLooped = False
            await ctx.send("Loop off")