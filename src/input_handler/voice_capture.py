import os
import subprocess
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class VoiceCapture:
    def __init__ ( self, whisper_bin :str ="whisper-cpp" , model_path: Optional [str ]=None):
        self.whisper_bin = whisper_bin


        self.model_path=model_path or os.environ.get("WHISPER_MODEL_PATH","models/ggml-base.en.bin" )
        self.sample_rate =16000
        self.duration_seconds = 5

    def is_available( self ) -> bool :

        if not os.path.isfile( self.model_path) :
            return False
        try :
            res = subprocess.run([self.whisper_bin, "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return res.returncode==0
        except FileNotFoundError:


            return False

    def capture_audio_chunk(self, duration: int = 5, output_wav: Optional[str] = None) -> str:
        if output_wav is None :
            fd,output_wav =tempfile.mkstemp ( suffix=".wav")
            os.close(fd)

        cmd = [
            "arecord",
            "-D", "default",
            "-r",str(self.sample_rate),
            "-c", "1",
            "-f", "S16_LE",
            "-d", str( duration),
            output_wav
        ]

        try:
            logger.info(f"Recording {duration}s audio to {output_wav}...")
            subprocess.run (cmd,check =True ,stdout=subprocess.PIPE , stderr =subprocess.PIPE)
            return output_wav
        except Exception as e :
            logger.warning(f"Failed to record audio via arecord: {e}")
            return output_wav

    def transcribe(self, wav_path: str) -> str:
        if not os.path.exists(wav_path )or os.path.getsize ( wav_path )==0:

            return ""

        if not os.path.exists(self.model_path):
            logger.warning(f"Whisper model not found at {self.model_path}. Returning simulated transcription." )
            return ""

        cmd = [
            self.whisper_bin ,
            "-m", self.model_path,
            "-f", wav_path,
            "--no-timestamps",
            "-nt"
        ]
        try:
            result = subprocess.run ( cmd , stdout=subprocess.PIPE ,stderr =subprocess.PIPE ,text= True , check =True )
            text = result.stdout.strip()
            # strip whisper artifact tokens
            text =text.replace("[BLANK_AUDIO]" , "" ).strip( )
            return text
        except Exception as e:
            logger.error (f"Whisper transcription failed: {e}")
            return ""

    def listen_and_transcribe (self ,duration : int=5 ) -> str :
        wav_path = self.capture_audio_chunk(duration=duration)
        try:
            return self.transcribe (wav_path)
        finally:
            if os.path.exists(wav_path):
                try:
                    os.remove( wav_path )
                except OSError :
                    pass
