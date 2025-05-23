import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import speech_recognition as sr
import requests
import pyaudio
import wave
import json
from imdb import Cinemagoer
from functools import reduce
from io import BytesIO
from gtts import gTTS

# Configuración de la API
TMDB_API_KEY = 'f6edbd8003bcfa3c2b4ceb48053fae1e'

# Cinemagoer. La IA que se encarga de buscar el titulo de películas
ia = Cinemagoer()

# Funciones principales

# Función para reconocer voz a partir de un archivo de audio
def reconocer_voz(archivo_audio):
    recognizer = sr.Recognizer()
    with sr.AudioFile(archivo_audio) as source:
        audio = recognizer.record(source)
    try:
        texto = recognizer.recognize_google(audio, language='es-ES')
        print(f"Texto reconocido por ASR: {texto}")
        return texto
    
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return "Error en la API de reconocimiento de voz."

# Función para analizar la consulta y extraer el título de la película y la información solicitada
def analizar_consulta(consulta):
    listaPretensiones = ["información", "casting", "reparto", "actores", "actriz", "director", "crew", "género", "categoría", "sinopsis", "descripción", "fecha", "lanzamiento", "estreno", "puntuación", "rating", "de", "dame", "dime", "todos", "los", "todas", "las"]
    pelicula = reduce(lambda acc, palabra: acc.replace(palabra, ''), listaPretensiones, consulta).strip()    
    resultados = ia.search_movie(pelicula)
    if resultados:
        pelicula = resultados[0]['title']
        informacion_solicitada = consulta.replace(pelicula, '').strip()
        print(f"Película identificada: {pelicula}")
        return pelicula, informacion_solicitada
    else:
        informacion_solicitada = consulta.replace(pelicula, '').strip()
        return pelicula, informacion_solicitada

# Función para obtener información de una película a partir de su título
def obtener_informacion_pelicula(pelicula):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={pelicula}&language=es-ES"
    response = requests.get(url)
    if response.status_code == 200:
        datos = response.json()
        if datos['results']:
            pelicula = datos['results'][0]
            titulo = pelicula['title']
            descripcion = pelicula['overview']
            fecha_lanzamiento = pelicula.get('release_date', 'No disponible')
            puntuacion = pelicula.get('vote_average', 'No disponible')
            poster_path = pelicula.get('poster_path', None)
            genres = pelicula.get('genre_ids', [])

            # Obtener reparto y equipo
            id_pelicula = pelicula['id']
            url_credits = f"https://api.themoviedb.org/3/movie/{id_pelicula}/credits?api_key={TMDB_API_KEY}&language=es-ES"
            response_credits = requests.get(url_credits)

            cast, crew = [], []
            if response_credits.status_code == 200:
                datos_credits = response_credits.json()
                cast = datos_credits.get('cast', [])
                crew = datos_credits.get('crew', [])

            return {
                "titulo": titulo,
                "descripcion": descripcion,
                "fecha_lanzamiento": fecha_lanzamiento,
                "puntuacion": puntuacion,
                "poster_path": poster_path,
                "genres": genres,
                "cast": cast,
                "crew": crew
            }
    return None

# Función para sintetizar voz a partir de un texto con gTTS
def sintetizar_voz(texto):
    tts = gTTS(text=texto, lang='es')
    audio_path = "./Respuestas/respuesta.mp3"
    tts.save(audio_path)
    return audio_path

# Función para grabar audio en tiempo real
def grabar_audio():
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = 5
    WAVE_OUTPUT_FILENAME = "./Consultas/consulta.wav"

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* Grabando...")
    frames = []

    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("* Grabación finalizada")

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

# Clase que se encarga de la gestión de ventanas y eventos de la interfaz
class Interfaz(tk.Tk):
    # Constructor de la clase
    def __init__(self):
        super().__init__()
        self.title("FilmMind")
        self.geometry("450x150")
        self.iconbitmap("./Icono/icono.ico")

        self.archivo_audio_cargado = None
        self.resultados_peliculas = []
        self.indice_pelicula_actual = 0
        self.informacion_solicitada = ""

        self.boton_subir_archivo = tk.Button(self, text="Cargar Consulta Grabada", command=self.subir_archivo)
        self.boton_subir_archivo.pack(pady=10)

        self.boton_grabar_audio = tk.Button(self, text="Grabar Consulta en Tiempo Real", command=self.grabar_consulta)
        self.boton_grabar_audio.pack(pady=10)

        self.boton_realizar_consulta = tk.Button(self, text="Realizar Consulta", command=self.realizar_consulta)
        self.boton_realizar_consulta.pack(pady=10)
        
        self.centrar_ventana(self)

    # Función para centrar una ventana en la pantalla
    def centrar_ventana(self, ventana):
        ventana.update_idletasks()  
        ancho_ventana = ventana.winfo_width()
        alto_ventana = ventana.winfo_height()
        ancho_pantalla = ventana.winfo_screenwidth()
        alto_pantalla = ventana.winfo_screenheight()

        # Calcular coordenadas para centrar
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2)

        # Establecer la geometría de la ventana
        ventana.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")

    # Funciones de eventos

    # Función para subir un archivo de audio
    def subir_archivo(self):
        archivo_audio = filedialog.askopenfilename(filetypes=[("Archivos de audio", "*.wav *.mp3")])
        if archivo_audio:
            self.archivo_audio_cargado = archivo_audio

    # Función para grabar una consulta en tiempo real
    def grabar_consulta(self):
        grabar_audio()
        self.archivo_audio_cargado = "./Consultas/consulta.wav"

    # Función para realizar una consulta
    def realizar_consulta(self):
        if self.archivo_audio_cargado:
            texto_consulta = reconocer_voz(self.archivo_audio_cargado)
            if not texto_consulta:
                messagebox.showerror("Error", "No se pudo reconocer el audio.")
                return

            pelicula, self.informacion_solicitada = analizar_consulta(texto_consulta)
            if not pelicula:
                messagebox.showerror("Error", "No se encontró ninguna película en la consulta.")
                return

            # Obtener múltiples resultados de la consulta
            url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={pelicula}&language=es-ES"
            response = requests.get(url)
            if response.status_code == 200:
                datos = response.json()
                if datos['results']:
                    # Guardar los resultados de la consulta
                    self.resultados_peliculas = datos['results']
                    self.indice_pelicula_actual = 0  # Reiniciar el índice

                    # Obtener información de la primera película
                    pelicula_actual = self.resultados_peliculas[self.indice_pelicula_actual]
                    info_pelicula = obtener_informacion_pelicula(pelicula_actual['title'])

                    if not info_pelicula:
                        messagebox.showerror("Error", "No se pudo obtener información de la película.")
                        return

                    respuesta_texto, archivo_respuesta_audio, casting, cast = self.generar_respuesta(info_pelicula, self.informacion_solicitada)
                    if casting:
                        self.mostrar_ventana_emergente_casting(cast, respuesta_texto, archivo_respuesta_audio)
                    else:
                        self.mostrar_ventana_emergente(info_pelicula, respuesta_texto, archivo_respuesta_audio)
                else:
                    messagebox.showerror("Error", "No se encontraron resultados para la consulta.")
            else:
                messagebox.showerror("Error", "Error al realizar la consulta a la API.")
        else:
            messagebox.showerror("Error", "No se ha cargado ningún archivo de audio.")

    # Función para generar una respuesta a partir de la información de la película y la información solicitada
    def generar_respuesta(self, info_pelicula, informacion_solicitada):
        respuesta_texto = ""
        casting = False
        cast = []
        
        if "género" in informacion_solicitada.lower() or "categoría" in informacion_solicitada.lower():
            respuesta_texto = self.get_Generos(info_pelicula)
        elif "sinopsis" in informacion_solicitada.lower() or "descripción" in informacion_solicitada.lower():
            respuesta_texto = info_pelicula.get('descripcion', "No se encontró la descripción de esta película.")
        elif "fecha" in informacion_solicitada.lower() or "lanzamiento" in informacion_solicitada.lower() or "estreno" in informacion_solicitada.lower():
            respuesta_texto = f"La fecha de lanzamiento de la película es {info_pelicula.get('fecha_lanzamiento', 'no disponible.')}."
        elif "puntuación" in informacion_solicitada.lower() or "rating" in informacion_solicitada.lower():
            respuesta_texto = f"La puntuación de la película es {info_pelicula.get('puntuacion', 'no disponible.')}"
        elif "reparto" in informacion_solicitada.lower() or "actores" in informacion_solicitada.lower() or "actriz" in informacion_solicitada.lower() or "cast" in informacion_solicitada.lower():
            casting = True 
            cast = info_pelicula.get('cast', [])
            if cast:
                respuesta_texto = "Reparto principal:\n" + "\n".join([f"{actor['name']} como {actor['character']}" for actor in cast[:10]])
            else:
                respuesta_texto = "No se encontró información del reparto."
        elif "director" in informacion_solicitada.lower() or "crew" in informacion_solicitada.lower():
            crew = info_pelicula.get('crew', [])
            directores = [persona['name'] for persona in crew if persona['job'].lower() == 'director']
            respuesta_texto = f"El director de la película es {', '.join(directores)}." if directores else "No se encontró información del director."
        else:
            respuesta_texto = f"Título: {info_pelicula.get('titulo', 'No disponible')}\n\nSinopsis: {info_pelicula.get('descripcion')} \n\nFecha de estreno {info_pelicula.get('fecha_lanzamiento', 'no disponible.')} \n\nPuntuación: {info_pelicula.get('puntuacion', 'no disponible.')} \n"

        archivo_respuesta_audio = sintetizar_voz(respuesta_texto)
        return respuesta_texto, archivo_respuesta_audio, casting, cast
    

    def get_Generos(self, info_pelicula):
        # Cargar el JSON auxiliar
        with open('./Generos/generosList.json', 'r') as file:
            generos_aux = json.load(file)

        # Crear un diccionario para mapear id de género a nombre
        id_a_nombre_genero = {genero['id']: genero['name'] for genero in generos_aux['genres']}

        # Obtener los géneros de la película
        idGeneros = [id_a_nombre_genero[genero] for genero in info_pelicula.get('genres', []) if genero in id_a_nombre_genero]

        # Generar la respuesta
        respuesta_texto = f"Los géneros de la película son: {', '.join(idGeneros)}." if idGeneros else "No se encontraron géneros para esta película."

        return respuesta_texto

    # Funciones de interfaz

    # Función para mostrar una ventana emergente con la información de la película
    def mostrar_ventana_emergente(self, info_pelicula, texto_respuesta, archivo_audio):
        ventana_emergente = tk.Toplevel(self)
        ventana_emergente.title("Resultado de la Consulta")
        ventana_emergente.iconbitmap("./Icono/icono.ico")

        # Mostrar el cartel de la película (si existe)
        poster_path = info_pelicula.get('poster_path')
        if poster_path:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            response = requests.get(poster_url)
            if response.status_code == 200:
                imagen_poster = Image.open(BytesIO(response.content))
                imagen_poster = imagen_poster.resize((300, 450), Image.LANCZOS)
                imagen_poster = ImageTk.PhotoImage(imagen_poster)
                label_imagen = tk.Label(ventana_emergente, image=imagen_poster)
                label_imagen.image = imagen_poster
                label_imagen.pack(pady=10)

        # Botón para oír la respuesta
        boton_oir_audio = tk.Button(ventana_emergente, text="Oír Respuesta", command=lambda: self.reproducir_audio(archivo_audio))
        boton_oir_audio.pack(pady=5)

        # Botón para ver la transcripción
        boton_ver_transcripcion = tk.Button(ventana_emergente, text="Ver Transcripción", command=lambda: self.mostrar_transcripcion(texto_respuesta))
        boton_ver_transcripcion.pack(pady=5)

        # Botón para pasar a la siguiente película
        boton_siguiente_pelicula = tk.Button(ventana_emergente, text="Siguiente Película", command=lambda: self.mostrar_siguiente_pelicula(ventana_emergente))
        boton_siguiente_pelicula.pack(pady=5)

        # Centrar la ventana emergente
        ventana_emergente.update_idletasks()  # Asegurarse de que la geometría está configurada
        self.centrar_ventana(ventana_emergente)
    
    # Función para mostrar una ventana emergente con el reparto de la película
    def mostrar_ventana_emergente_casting(self, casting, texto_respuesta, archivo_audio):
        ventana_emergente_reparto = tk.Toplevel(self)
        ventana_emergente_reparto.title("Reparto de la Película")
        ventana_emergente_reparto.iconbitmap("./Icono/icono.ico")

        # Mostrar los actores y sus personajes en 4 filas de 2 columnas
        for i in range(4):
            for j in range(2):
                idx = i * 2 + j
                if idx < len(casting):
                    actor = casting[idx]
                    poster_url = f"https://image.tmdb.org/t/p/w500{actor.get('profile_path', '')}"
                    response = requests.get(poster_url)
                    if response.status_code == 200:
                        imagen_actor = Image.open(BytesIO(response.content))
                        imagen_actor = imagen_actor.resize((100, 125), Image.LANCZOS)
                        imagen_actor = ImageTk.PhotoImage(imagen_actor)
                        label_imagen = tk.Label(ventana_emergente_reparto, image=imagen_actor)
                        label_imagen.image = imagen_actor
                        label_imagen.grid(row=i, column=j*2, padx=10, pady=10)
                    
                    label_nombre = tk.Label(ventana_emergente_reparto, text=f"{actor['name']} como {actor['character']}")
                    label_nombre.grid(row=i, column=j*2+1, padx=10, pady=10)

        # Crear un marco para los botones y colocarlos con .grid()
        frame_botones = tk.Frame(ventana_emergente_reparto)
        frame_botones.grid(row=4, column=0, columnspan=4, pady=10)  # Colocar el marco debajo del reparto

        # Botón para oír la respuesta
        boton_oir_audio = tk.Button(frame_botones, text="Oír Respuesta", command=lambda: self.reproducir_audio(archivo_audio))
        boton_oir_audio.grid(row=0, column=0, padx=5)

        # Botón para ver la transcripción
        boton_ver_transcripcion = tk.Button(frame_botones, text="Ver Transcripción", command=lambda: self.mostrar_transcripcion(texto_respuesta))
        boton_ver_transcripcion.grid(row=0, column=1, padx=5)

        # Centrar la ventana emergente
        ventana_emergente_reparto.update_idletasks()  # Asegurarse de que la geometría está configurada
        self.centrar_ventana(ventana_emergente_reparto)

    # Función para mostrar la transcripción de la respuesta
    def mostrar_transcripcion(self, texto_respuesta):
        # Crear una nueva ventana para mostrar la transcripción
        ventana_transcripcion = tk.Toplevel(self)
        ventana_transcripcion.title("Transcripción de la Respuesta")
        ventana_transcripcion.iconbitmap("./Icono/icono.ico")

        # Mostrar la transcripción en la nueva ventana
        texto = tk.Text(ventana_transcripcion, wrap=tk.WORD, width=50, height=20)
        texto.insert(tk.END, texto_respuesta)
        texto.config(state=tk.DISABLED) 
        texto.pack(pady=10)

        boton_cerrar = tk.Button(ventana_transcripcion, text="Cerrar", command=ventana_transcripcion.destroy)
        boton_cerrar.pack(pady=5)

        # Centrar la ventana emergente
        ventana_transcripcion.update_idletasks()  # Asegurarse de que la geometría está configurada
        self.centrar_ventana(ventana_transcripcion)

    # Función para mostrar la siguiente película en los resultados
    def mostrar_siguiente_pelicula(self, ventana_actual):
        self.indice_pelicula_actual += 1

        if self.indice_pelicula_actual < len(self.resultados_peliculas):
            pelicula_actual = self.resultados_peliculas[self.indice_pelicula_actual]
            info_pelicula = self.resultados_peliculas[self.indice_pelicula_actual]

            if info_pelicula:
                texto_respuesta, archivo_respuesta_audio, casting, cast = self.generar_respuesta(info_pelicula, self.informacion_solicitada)
                ventana_actual.destroy() 
                if casting:
                    self.mostrar_ventana_emergente_casting(cast, texto_respuesta, archivo_respuesta_audio)
                else:
                    self.mostrar_ventana_emergente(info_pelicula, texto_respuesta, archivo_respuesta_audio)
            else:
                messagebox.showerror("Error", "No se pudo obtener información de la siguiente película.")
                ventana_actual.destroy()
        else:
            messagebox.showinfo("Fin de Resultados", "No hay más películas en los resultados.")
            ventana_actual.destroy()

    # Función para reproducir un archivo de audio
    def reproducir_audio(self, archivo_audio):
        if os.path.exists(archivo_audio):
            os.system(f"start {archivo_audio}")
        else:
            messagebox.showerror("Error", "No se encontró el archivo de audio.")

# Función principal
if __name__ == "__main__":
    app = Interfaz()
    app.mainloop()

