"""Dinámicas de primaria con respuestas verificables y sesiones independientes."""

import copy
import random
import re
import threading
import time
import unicodedata
import uuid

SUBJECTS = {
    'mixto': 'Un poco de todo',
    'matematicas': 'Matemáticas',
    'ciencias_naturales': 'Ciencias naturales',
    'geografia': 'Geografía',
    'biologia': 'Biología',
    'espanol': 'Español',
}
TOTAL = 5

# Cada registro contiene pregunta, respuesta, distractores y explicación.
# Los grupos corresponden a 1.º–2.º, 3.º–4.º y 5.º–6.º de primaria.
BANK = {
    'ciencias_naturales': [
        [
            ('¿Qué nos da luz y calor durante el día?', 'El Sol', ['La Luna', 'Una piedra', 'Una nube'], 'El Sol es una estrella que nos proporciona luz y calor.'),
            ('¿En qué se convierte el agua cuando se congela?', 'Hielo', ['Arena', 'Aceite', 'Humo'], 'Al congelarse, el agua pasa de líquida a sólida y forma hielo.'),
            ('¿Con qué sentido puedes escuchar una canción?', 'El oído', ['La vista', 'El gusto', 'El olfato'], 'El oído nos permite escuchar los sonidos.'),
            ('¿Qué debes hacer con la basura para cuidar tu escuela?', 'Ponerla en el bote', ['Tirarla al suelo', 'Dejarla en el río', 'Esconderla bajo una planta'], 'Poner la basura en el bote ayuda a mantener limpio nuestro entorno.'),
            ('¿Qué usamos para protegernos de la lluvia?', 'Un paraguas', ['Un tenedor', 'Un cuaderno', 'Una pelota'], 'El paraguas ayuda a evitar que la lluvia moje nuestro cuerpo.'),
        ],
        [
            ('¿Cómo se llama el cambio del agua líquida a vapor?', 'Evaporación', ['Congelación', 'Germinación', 'Digestión'], 'En la evaporación, el agua líquida se transforma en vapor.'),
            ('¿Cuál de estos materiales suele ser atraído por un imán?', 'Hierro', ['Madera', 'Papel', 'Plástico'], 'Los imanes atraen algunos metales, como el hierro.'),
            ('¿Cuál es un ejemplo de agua en estado sólido?', 'Un cubo de hielo', ['Agua de un vaso', 'Vapor de agua', 'Una gota de lluvia'], 'El hielo es agua en estado sólido.'),
            ('¿Qué instrumento sirve para medir la temperatura?', 'Termómetro', ['Regla', 'Brújula', 'Balanza'], 'El termómetro mide la temperatura.'),
            ('¿Qué acción ayuda a ahorrar agua?', 'Cerrar la llave al cepillarse', ['Dejar la llave abierta', 'Lavar la banqueta con mucha agua', 'Ignorar una fuga'], 'Cerrar la llave cuando no la necesitamos evita desperdiciar agua.'),
        ],
        [
            ('¿Qué movimiento de la Tierra produce el día y la noche?', 'Rotación', ['Traslación', 'Evaporación', 'Germinación'], 'La rotación es el giro de la Tierra sobre su propio eje.'),
            ('¿Qué necesita un circuito sencillo para que encienda su foco?', 'Estar cerrado', ['Tener un cable cortado', 'Estar abierto', 'Estar desconectado'], 'En un circuito cerrado, la corriente puede recorrer el camino completo.'),
            ('¿Cuál es una fuente de energía renovable?', 'El viento', ['El petróleo', 'El carbón', 'El gas natural'], 'El viento se renueva de forma natural y puede usarse para generar electricidad.'),
            ('¿Cómo se llama el cambio del vapor de agua a agua líquida?', 'Condensación', ['Evaporación', 'Fusión', 'Congelación'], 'La condensación ocurre cuando el vapor de agua se transforma en líquido.'),
            ('¿Qué mezcla se puede separar usando un filtro?', 'Agua y arena', ['Agua y sal disuelta', 'Agua y azúcar disuelta', 'Dos cantidades de agua'], 'El filtro retiene los granos de arena y deja pasar el agua.'),
        ],
    ],
    'biologia': [
        [
            ('¿Qué parte de una planta absorbe agua del suelo?', 'La raíz', ['La flor', 'El fruto', 'La semilla'], 'Las raíces absorben agua del suelo y ayudan a sujetar la planta.'),
            ('¿Qué animal es un mamífero?', 'El perro', ['La mariposa', 'La gallina', 'La rana'], 'El perro es un mamífero; las madres alimentan a sus crías con leche.'),
            ('¿Con qué órganos respiramos las personas?', 'Los pulmones', ['Los huesos', 'Los dientes', 'Los ojos'], 'Los pulmones participan en la respiración.'),
            ('¿Qué necesita una planta para crecer?', 'Agua y luz', ['Solo juguetes', 'Solo piedras', 'Solo pintura'], 'Las plantas necesitan agua y luz, además de aire y nutrientes.'),
            ('¿Qué acción ayuda a evitar enfermedades antes de comer?', 'Lavarse las manos', ['Ensuciar el plato', 'Comer tierra', 'Compartir un cepillo de dientes'], 'Lavarse las manos ayuda a quitar suciedad y muchos microbios.'),
        ],
        [
            ('¿Cómo se llama un animal que come principalmente plantas?', 'Herbívoro', ['Carnívoro', 'Omnívoro', 'Invertebrado'], 'Un herbívoro se alimenta principalmente de plantas.'),
            ('¿Qué característica tienen los animales vertebrados?', 'Columna vertebral', ['Siempre seis patas', 'Siempre alas', 'Siempre antenas'], 'Los vertebrados tienen columna vertebral.'),
            ('¿Qué órgano bombea la sangre?', 'El corazón', ['El estómago', 'La lengua', 'La piel'], 'El corazón impulsa la sangre por el cuerpo.'),
            ('¿Cuántas patas tiene un insecto adulto?', '6', ['4', '8', '10'], 'Los insectos adultos tienen seis patas.'),
            ('¿Qué proceso permite que una semilla empiece a crecer?', 'Germinación', ['Digestión', 'Evaporación', 'Rotación'], 'La germinación es el inicio del crecimiento de una planta desde su semilla.'),
        ],
        [
            ('¿Cuál es la unidad básica de los seres vivos?', 'La célula', ['Una piedra', 'Un planeta', 'Una nube'], 'La célula es la unidad básica de estructura y funcionamiento de los seres vivos.'),
            ('¿Qué seres vivos son productores en una cadena alimentaria?', 'Las plantas', ['Los leones', 'Los conejos', 'Las águilas'], 'Las plantas producen su alimento mediante la fotosíntesis.'),
            ('¿En qué órgano se absorbe la mayor parte de los nutrientes de los alimentos?', 'Intestino delgado', ['Esófago', 'Boca', 'Pulmones'], 'El intestino delgado absorbe la mayor parte de los nutrientes de los alimentos.'),
            ('¿Qué gas del aire utiliza nuestro cuerpo para la respiración?', 'Oxígeno', ['Helio', 'Hidrógeno', 'Metano'], 'Nuestro cuerpo utiliza oxígeno para obtener energía de los nutrientes.'),
            ('¿Qué es un ecosistema?', 'Seres vivos y su ambiente', ['Solo animales', 'Solo agua', 'Solo piedras'], 'Un ecosistema incluye seres vivos, su ambiente y las relaciones entre ellos.'),
        ],
    ],
    'geografia': [
        [
            ('¿En qué país está Mexicali?', 'México', ['Canadá', 'Brasil', 'España'], 'Mexicali es una ciudad de México.'),
            ('¿Qué nos ayuda a encontrar lugares y caminos?', 'Un mapa', ['Una cuchara', 'Una almohada', 'Un zapato'], 'Un mapa representa lugares y nos ayuda a orientarnos.'),
            ('¿Cuál de estos lugares contiene una gran cantidad de agua salada?', 'El mar', ['Una montaña', 'Un desierto', 'Una escuela'], 'El mar contiene agua salada.'),
            ('¿Cuál es un punto cardinal?', 'Norte', ['Caliente', 'Grande', 'Rápido'], 'Los puntos cardinales principales son norte, sur, este y oeste.'),
            ('¿Cómo se llama el planeta donde vivimos?', 'Tierra', ['Marte', 'Júpiter', 'Venus'], 'La Tierra es el planeta donde vivimos.'),
        ],
        [
            ('¿Cuál es la capital de México?', 'Ciudad de México', ['Mexicali', 'Guadalajara', 'Monterrey'], 'La capital de nuestro país es Ciudad de México.'),
            ('¿En qué continente está México?', 'América', ['Europa', 'África', 'Oceanía'], 'México se encuentra en América.'),
            ('¿Cuál es la capital de Baja California?', 'Mexicali', ['Tijuana', 'Ensenada', 'La Paz'], 'Mexicali es la capital del estado de Baja California.'),
            ('¿Qué océano está al oeste de México?', 'Pacífico', ['Atlántico', 'Índico', 'Ártico'], 'El océano Pacífico se encuentra al oeste de México.'),
            ('¿Qué instrumento ayuda a encontrar el norte?', 'Brújula', ['Termómetro', 'Balanza', 'Cronómetro'], 'La brújula ayuda a orientarnos e identificar direcciones.'),
        ],
        [
            ('¿Cómo se llama la línea imaginaria que divide la Tierra en hemisferios norte y sur?', 'Ecuador', ['Meridiano de Greenwich', 'Trópico de Cáncer', 'Círculo polar ártico'], 'El ecuador divide la Tierra en hemisferios norte y sur.'),
            ('¿Qué coordenada indica qué tan al norte o al sur está un lugar?', 'Latitud', ['Longitud', 'Altitud', 'Temperatura'], 'La latitud mide la posición al norte o al sur del ecuador.'),
            ('¿Qué describe el clima de un lugar?', 'Condiciones del tiempo durante muchos años', ['Solo la lluvia de hoy', 'Solo la hora actual', 'Solo el nombre de una ciudad'], 'El clima describe patrones del tiempo observados durante muchos años.'),
            ('¿Qué representa la escala de un mapa?', 'Relación entre distancias del mapa y reales', ['La temperatura', 'La cantidad de árboles', 'La edad del mapa'], 'La escala relaciona una distancia del mapa con la distancia real.'),
            ('¿Qué es la migración de personas?', 'Cambiar de lugar de residencia', ['Leer un mapa', 'Medir una montaña', 'Cambiar de ropa'], 'La migración consiste en cambiar de lugar de residencia, dentro de un país o hacia otro.'),
        ],
    ],
    'espanol': [
        [
            ('¿Con qué letra empieza la palabra casa?', 'C', ['M', 'P', 'S'], 'La palabra casa empieza con la letra c.'),
            ('¿Cuál de estas letras es una vocal?', 'A', ['B', 'D', 'F'], 'Las vocales son a, e, i, o y u.'),
            ('¿Cuántas sílabas tiene la palabra mesa?', '2', ['1', '3', '4'], 'Mesa tiene dos sílabas: me y sa.'),
            ('¿Qué palabra significa lo contrario de grande?', 'Pequeño', ['Enorme', 'Gigante', 'Amplio'], 'Grande y pequeño tienen significados opuestos.'),
            ('¿Qué signo usamos normalmente al final de una oración que afirma algo?', 'Punto', ['Signo de interrogación', 'Signo de suma', 'Signo de igual'], 'El punto marca el final de una oración que afirma algo.'),
        ],
        [
            ('En la oración Ana corre, ¿qué palabra es el verbo?', 'Corre', ['Ana', 'La', 'Una'], 'Corre es el verbo porque expresa la acción.'),
            ('¿Cuál es un sinónimo de feliz?', 'Contento', ['Triste', 'Enojado', 'Cansado'], 'Feliz y contento tienen significados semejantes.'),
            ('¿Cuál es el plural de lápiz?', 'Lápices', ['Lápizs', 'Lapiz', 'Lápiza'], 'El plural de lápiz se escribe lápices.'),
            ('En la frase pelota roja, ¿qué palabra describe a la pelota?', 'Roja', ['Pelota', 'Frase', 'Una'], 'Roja es un adjetivo porque describe una característica de la pelota.'),
            ('¿Qué signos rodean una pregunta escrita en español?', 'Signos de interrogación', ['Solo comas', 'Paréntesis siempre', 'Signos de suma'], 'En español usamos un signo de interrogación al inicio y otro al final de la pregunta.'),
        ],
        [
            ('En la oración María lee un cuento, ¿quién es el sujeto?', 'María', ['Lee', 'Un cuento', 'Un'], 'María es el sujeto porque es quien realiza la acción.'),
            ('¿Cuál de estas palabras es aguda y lleva tilde?', 'Café', ['Mesa', 'Árbol', 'Pájaro'], 'Café es aguda: su sílaba más fuerte es la última y lleva tilde porque termina en vocal.'),
            ('¿Cuál es un sustantivo colectivo?', 'Rebaño', ['Oveja', 'Lápiz', 'Niño'], 'Rebaño nombra un conjunto de animales, por eso es un sustantivo colectivo.'),
            ('¿Qué palabra puede sustituir a Ana en Ana canta?', 'Ella', ['Nosotros', 'Ellos', 'Yo'], 'Ella es un pronombre que puede sustituir a Ana en esa oración.'),
            ('¿Qué texto cuenta una historia con personajes?', 'Un cuento', ['Una lista de compras', 'Un horario', 'Una tabla de números'], 'Un cuento narra una historia que tiene personajes y acontecimientos.'),
        ],
    ],
}


def normalize(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text.casefold()) if unicodedata.category(c) != 'Mn')
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text).split())


def number_words(number):
    small = ['cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciseis', 'diecisiete', 'dieciocho', 'diecinueve', 'veinte', 'veintiuno', 'veintidos', 'veintitres', 'veinticuatro', 'veinticinco', 'veintiseis', 'veintisiete', 'veintiocho', 'veintinueve']
    if 0 <= number < 30:
        return small[number]
    if 30 <= number < 100:
        tens = {3: 'treinta', 4: 'cuarenta', 5: 'cincuenta', 6: 'sesenta', 7: 'setenta', 8: 'ochenta', 9: 'noventa'}
        return tens[number // 10] + (' y ' + small[number % 10] if number % 10 else '')
    return str(number)


def math_question(grade, rng):
    if grade <= 2:
        maximum = 5 if grade == 1 else 25
        a, b = rng.randint(1, maximum), rng.randint(1, maximum)
        if rng.choice([True, False]):
            prompt = f'Tienes {a} lápices y te regalan {b} más. ¿Cuántos lápices tienes ahora?'
            answer = a + b
            explanation = f'Sumamos {a} más {b} y obtenemos {answer}.'
        else:
            a, b = max(a, b), min(a, b)
            prompt = f'Tienes {a} lápices y prestas {b}. ¿Cuántos te quedan?'
            answer = a - b
            explanation = f'Restamos {b} a {a} y nos {"queda" if answer == 1 else "quedan"} {answer}.'
    elif grade <= 4:
        a, b = rng.randint(2, 9 if grade == 3 else 15), rng.randint(2, 9)
        if rng.choice([True, False]):
            prompt = f'Hay {a} cajas con {b} colores en cada caja. ¿Cuántos colores hay en total?'
            answer = a * b
            explanation = f'Multiplicamos {a} por {b} y obtenemos {answer}.'
        else:
            prompt = f'Repartes {a * b} colores por igual entre {b} niños. ¿Cuántos recibe cada niño?'
            answer = a
            explanation = f'Dividimos {a * b} entre {b} y cada niño recibe {answer}.'
    elif grade == 5:
        denominator = rng.choice([2, 3, 4, 5, 10])
        answer = rng.randint(2, 12)
        total = denominator * answer
        prompt = f'¿Cuánto es un { {2: "medio", 3: "tercio", 4: "cuarto", 5: "quinto", 10: "décimo"}[denominator]} de {total}?'
        explanation = f'Dividimos {total} entre {denominator} y obtenemos {answer}.'
    else:
        percentage = rng.choice([10, 25, 50])
        total = rng.choice([20, 40, 60, 80, 100, 200])
        answer = total * percentage // 100
        prompt = f'¿Cuánto es el {percentage} por ciento de {total}?'
        explanation = f'El {percentage} por ciento de {total} equivale a {answer}.'
    wrong = {max(0, answer + offset) for offset in [-3, -2, -1, 1, 2, 3, 5]}
    wrong.discard(answer)
    return prompt, str(answer), [str(n) for n in rng.sample(sorted(wrong), 3)], explanation


def make_questions(grade, subject, rng):
    band = (grade - 1) // 2
    subjects = list(BANK) + ['matematicas'] if subject == 'mixto' else [subject]
    pool = []
    for name in subjects:
        entries = []
        if name == 'matematicas':
            seen = set()
            while len(entries) < TOTAL:
                entry = math_question(grade, rng)
                if entry[0] not in seen:
                    entries.append(entry)
                    seen.add(entry[0])
        else:
            entries = BANK[name][band]
        for prompt, answer, distractors, explanation in entries:
            options = [answer, *distractors]
            rng.shuffle(options)
            pool.append({'id': str(uuid.uuid4()), 'prompt': prompt, 'options': options, 'answer': answer, 'explanation': explanation, 'subject': SUBJECTS[name]})
    if subject == 'mixto':
        rng.shuffle(subjects)
        return [rng.choice([q for q in pool if q['subject'] == SUBJECTS[name]]) for name in subjects]
    return rng.sample(pool, TOTAL)


def pick_answer(text, question):
    value = normalize(text)
    options = question['options']
    def aliases_for(option):
        aliases = {normalize(option)}
        if option.isdigit():
            aliases.add(number_words(int(option)))
            if option == '1':
                aliases.update({'un', 'una'})
        pronunciation = {'B': 'be', 'C': 'ce', 'D': 'de', 'F': 'efe', 'M': 'eme', 'P': 'pe', 'S': 'ese'}
        if option in pronunciation:
            aliases.add(pronunciation[option])
        return aliases
    # Las respuestas literales tienen prioridad: "a" puede ser una vocal.
    for option in options:
        if value in aliases_for(option):
            return option
    letter = re.fullmatch(r'(?:(?:la )?(?:opcion|letra|respuesta)(?: es)? )?([abcd]|be|ce|de)', value)
    if letter:
        code = {'be': 'b', 'ce': 'c', 'de': 'd'}.get(letter.group(1), letter.group(1))
        return options[ord(code) - ord('a')]
    prefix = r'^(?:(?:creo que )?(?:la respuesta es|es|son)|el|la|los|las|un|una|unos|unas) '
    def strip_prefix(text):
        while True:
            stripped = re.sub(prefix, '', text)
            if stripped == text:
                return text
            text = stripped
    value = strip_prefix(value)
    for option in options:
        aliases = {strip_prefix(alias) for alias in aliases_for(option)}
        if value in aliases:
            return option
    if value in {'no se', 'no lo se', 'no recuerdo', 'paso'}:
        return None
    raise ValueError('Elige una opción, escribe su texto o di la letra A, B, C o D. También puedes decir no sé.')


class QuizService:
    def __init__(self):
        self.sessions = {}
        self.lock = threading.RLock()

    def _get(self, session_id):
        session = self.sessions.get(session_id)
        if session is None or time.monotonic() - session['updated'] > 7200:
            self.sessions.pop(session_id, None)
            raise KeyError('Esta dinámica terminó o se reinició el servidor. Inicia un juego nuevo.')
        session['updated'] = time.monotonic()
        return session

    def _view(self, session):
        question = session['questions'][session['index']]
        phase = session['phase']
        intro = f'Pregunta {session["index"] + 1} de {TOTAL}. '
        spoken_options = '. '.join(f'{chr(65 + i)}, {option}' for i, option in enumerate(question['options']))
        response = intro + question['prompt'] + ' Opciones: ' + spoken_options + '.'
        if phase in {'feedback', 'finished'}:
            response = session['feedback']['text']
        if phase == 'finished':
            response += f' ¡Terminamos! Acertaste {session["score"]} de {TOTAL}. Cada pregunta nos ayuda a aprender. ¡Gracias por jugar conmigo!'
        return {
            'session_id': session['id'], 'grade': session['grade'], 'subject': session['subject'],
            'subject_label': SUBJECTS[session['subject']], 'total': TOTAL, 'answered': len(session['answers']),
            'score': session['score'], 'phase': phase,
            'question': {'id': question['id'], 'prompt': question['prompt'], 'subject': question['subject'], 'options': [{'label': chr(65 + i), 'text': option} for i, option in enumerate(question['options'])]},
            'feedback': copy.deepcopy(session.get('feedback')), 'response': response,
        }

    def start(self, grade, subject):
        if grade not in range(1, 7) or subject not in SUBJECTS:
            raise ValueError('Elige un grado de primero a sexto y una materia válida.')
        with self.lock:
            now = time.monotonic()
            self.sessions = {key: value for key, value in self.sessions.items() if now - value['updated'] <= 7200}
            if len(self.sessions) >= 500:
                oldest = min(self.sessions, key=lambda key: self.sessions[key]['updated'])
                del self.sessions[oldest]
            questions = make_questions(grade, subject, random.Random())[:TOTAL]
            session = {'id': str(uuid.uuid4()), 'grade': grade, 'subject': subject, 'questions': questions, 'index': 0, 'score': 0, 'phase': 'question', 'answers': {}, 'feedback': None, 'updated': now}
            self.sessions[session['id']] = session
            result = self._view(session)
            grade_name = {1: 'primero', 2: 'segundo', 3: 'tercero', 4: 'cuarto', 5: 'quinto', 6: 'sexto'}[grade]
            result['response'] = f'¡Vamos a jugar! Practicaremos temas de {grade_name} de primaria. ' + result['response']
            return result

    def answer(self, session_id, question_id, text):
        with self.lock:
            session = self._get(session_id)
            if question_id in session['answers']:
                return copy.deepcopy(session['answers'][question_id])
            question = session['questions'][session['index']]
            if session['phase'] != 'question' or question['id'] != question_id:
                raise ValueError('Esa pregunta ya no está activa. Continúa con la pregunta que aparece en pantalla.')
            chosen = pick_answer(text, question)
            correct = chosen == question['answer']
            session['score'] += int(correct)
            feedback = ('¡Muy bien! ' if correct else f'¡Buen intento! La respuesta es {question["answer"]}. ') + question['explanation']
            session['feedback'] = {'correct': correct, 'text': feedback, 'correct_answer': question['answer']}
            session['phase'] = 'finished' if session['index'] == TOTAL - 1 else 'feedback'
            # Reservar la respuesta antes de construir el contador público.
            session['answers'][question_id] = None
            result = self._view(session)
            session['answers'][question_id] = copy.deepcopy(result)
            return result

    def next(self, session_id, question_id):
        with self.lock:
            session = self._get(session_id)
            current = session['questions'][session['index']]
            if current['id'] != question_id and question_id in session['answers']:
                return self._view(session)
            if session['phase'] == 'finished':
                return self._view(session)
            if session['phase'] != 'feedback' or current['id'] != question_id:
                raise ValueError('Responde la pregunta actual antes de continuar.')
            session['index'] += 1
            session['phase'] = 'question'
            session['feedback'] = None
            return self._view(session)

    def end(self, session_id):
        with self.lock:
            self.sessions.pop(session_id, None)


quiz_service = QuizService()
