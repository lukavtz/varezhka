"""Build the illustrated Russian workflow guide with bundled Noto fonts."""
from pathlib import Path
from xml.sax.saxutils import escape
import re

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'guide'
OUT.mkdir(exist_ok=True)
PDF=OUT/'cartoon-workflow-guide.pdf'
pdfmetrics.registerFont(TTFont('Noto',str(ROOT/'assets/fonts/NotoSans-Regular.ttf')))
pdfmetrics.registerFont(TTFont('NotoBold',str(ROOT/'assets/fonts/NotoSans-Bold.ttf')))
pdfmetrics.registerFontFamily('Noto',normal='Noto',bold='NotoBold',italic='Noto',boldItalic='NotoBold')
W,H=A4
M=38
CW=W-2*M
BG=colors.HexColor('#F4F0E6')
INK=colors.HexColor('#273C40')
MUTED=colors.HexColor('#65777A')
ACCENT=colors.HexColor('#B96D42')
TEAL=colors.HexColor('#DCE7E2')
WHITE=colors.white
c=canvas.Canvas(str(PDF),pagesize=A4)
c.setTitle('Мультфильмы в Blender: переносимый workflow')
c.setAuthor('Cartoon Workflow Kit')
c.setSubject('Бриф, нативный рисунок, анимация, камера, голос, SFX и проверка')
PAGE=0


def spaced(text):
    text=re.sub(r'(?<=[А-Яа-яЁё])(?=\d)|(?<=\d)(?=[А-Яа-яЁё])',' ',text)
    return re.sub(r'(\d)(fps|LUFS|dBTP)\b',r'\1 \2',text)


def para(text,x,y,width,size=10.3,color=INK,bold=False,leading=None):
    style=ParagraphStyle('body',fontName='NotoBold' if bold else 'Noto',fontSize=size,
        leading=leading or size*1.45,textColor=color,spaceAfter=0)
    p=Paragraph(spaced(text),style)
    _,height=p.wrap(width,H)
    if y+height>H-43:raise ValueError('Text outside page: '+text[:80])
    p.drawOn(c,x,H-y-height)
    return y+height


def page(kicker,title,subtitle=''):
    global PAGE
    if PAGE:c.showPage()
    PAGE+=1
    c.setFillColor(BG);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(ACCENT);c.rect(M,H-35,29,4,fill=1,stroke=0)
    para(kicker.upper(),M,48,CW,8.5,MUTED,bold=True)
    y=para(title,M,69,CW,25,INK,bold=True,leading=31)
    if subtitle:y=para(subtitle,M,y+11,CW,10,MUTED)
    c.setStrokeColor(colors.HexColor('#C9D1C8'));c.line(M,32,W-M,32)
    c.setFont('Noto',7);c.setFillColor(MUTED)
    c.drawString(M,19,'CARTOON WORKFLOW KIT  /  04.11.2026')
    c.drawRightString(W-M,19,f'{PAGE:02d} / 13')
    c.bookmarkPage(f'p{PAGE}');c.addOutlineEntry(title,f'p{PAGE}',0)
    return y+23


def bullet(text,y,x=M,width=CW):
    c.setFillColor(ACCENT);c.circle(x+3,H-y-7,2,fill=1,stroke=0)
    return para(text,x+15,y,width-15)+11


def sub(title,y):
    return para(title,M,y,CW,13,INK,bold=True)+10


def table(rows,y,widths=None):
    widths=widths or [CW/len(rows[0])]*len(rows[0])
    content=[]
    for i,row in enumerate(rows):
        style=ParagraphStyle('cell',fontName='NotoBold' if i==0 else 'Noto',fontSize=9.1,
            leading=13,textColor=WHITE if i==0 else INK)
        content.append([Paragraph(spaced(escape(str(v))),style) for v in row])
    t=Table(content,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),INK),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#E5E9DF'),colors.HexColor('#F9F7EF')]),
        ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    _,height=t.wrap(CW,H)
    if y+height>H-48:raise ValueError('Table outside page')
    t.drawOn(c,M,H-y-height)
    return y+height+15


def picture(path,y,height,width=CW,x=M):
    image=ImageReader(str(ROOT/path));iw,ih=image.getSize()
    scale=min(width/iw,height/ih);dw,dh=iw*scale,ih*scale
    c.setFillColor(WHITE);c.rect(x,H-y-height,width,height,fill=1,stroke=0)
    c.drawImage(image,x+(width-dw)/2,H-y-height+(height-dh)/2,dw,dh)
    return y+height+12


def callout(text,y):
    style=ParagraphStyle('callout',fontName='Noto',fontSize=10,leading=14.5,textColor=INK)
    p=Paragraph(spaced(text),style);_,height=p.wrap(CW-28,H)
    if y+height+24>H-45:raise ValueError('Callout outside page')
    c.setFillColor(TEAL);c.roundRect(M,H-y-height-24,CW,height+24,9,fill=1,stroke=0)
    p.drawOn(c,M+14,H-y-height-12)
    return y+height+38


def code(lines,y):
    # Each displayed line is a complete command; fit it rather than inserting
    # shell-breaking line wraps without a continuation character.
    size=min(9.5,min((CW-28)/max(1,pdfmetrics.stringWidth(line,'Noto',1)) for line in lines))
    height=len(lines)*16+22
    c.setFillColor(TEAL);c.roundRect(M,H-y-height,CW,height,9,fill=1,stroke=0)
    c.setFont('Noto',size);c.setFillColor(INK)
    for index,line in enumerate(lines):c.drawString(M+14,H-y-19-index*16,line)
    return y+height+16


y=page('Практическое руководство','Мультфильмы<br/>в Blender',
    'Переносимый набор для агента: от выбора идеи до проверенного видео')
y=para('Рисунок, движение, камера и звук',M,y+4,CW,17,ACCENT,bold=True)+20
y=picture(Path('examples/stills/05-explaining-floorplan.png'),y,292)
y=para('Основано на реальных правках: цельные руки, кисти-варежки, два читаемых глаза, контакт с реквизитом, масштаб, полезные детали среды и осмысленные приближения камеры.',M,y+6,CW,12,leading=18)+21
callout('Начни с <b>prompts/START-HERE.txt</b>. Этот PDF объясняет процесс человеку; SKILL.md и исходники дают агенту рабочие инструкции.',y)

y=page('01 / Быстрый старт','Одна папка для нового агента')
for text in [
    '<b>Распакуй набор</b> и открой его как рабочую папку агента. Все пути внутри относительные.',
    '<b>Вставь START-HERE.txt.</b> Агент читает README и основной скилл, затем спрашивает только недостающие параметры.',
    '<b>Выбери бриф.</b> Формат, рисунок, тема, аудитория, реклама, длина, голос и субтитры.',
    '<b>Проверь инструменты.</b> Blender и Python нужны для картинок; ffmpeg - для MP4. MCP подключается отдельно.',
    '<b>Посмотри конкретный пример.</b> Сначала кадры и короткая проба, затем длинный рендер. При выбранной автономной работе агент проверяет и продолжает сам.'
]:y=bullet(text,y)
y=para('Путь к Blender укажи через BLENDER_PATH или флаг --blender, как в README.',M,y,CW,9.5)+10
y=code(['python scripts/doctor.py --json',
    'python scripts/render_example.py --mode stills --output output/example'],y+9)
y=sub('Озвучка не нужна для выбора идеи',y)
y=para('Готовый MP3, ElevenLabs, локальный голос или фильм без речи - отдельный выбор. Свой API-ключ добавляется локально в окружение только для озвучки; в чат и в переносимую папку он не попадает.',M,y,CW)
callout('Команды примеров проверяют среду и показывают подход. Они не создают новый фильм по произвольному брифу одним запуском.',y+20)

y=page('02 / Бриф','Что агент спросит сначала')
y=table([
    ['Решение','Варианты'],
    ['Экран','Горизонталь16:9 / вертикаль9:16 / обе версии с отдельной компоновкой'],
    ['Рисунок','Плоский мультфильм / пиксельный / стилизованный3D'],
    ['Задача','История / объяснение / развлечение / реклама'],
    ['Тема','Своя тема или2-3 идеи от агента; для кого и на каком языке'],
    ['Реклама','Нет / финальный CTA / встроенная; объект рекламы и ссылка'],
    ['Длина','30-60секунд / до90секунд / около3минут / точное значение'],
    ['Речь и текст','Готовая запись / ElevenLabs / локальный голос / без речи; один или несколько голосов; слова / фразы / без субтитров'],
    ['Контроль','Показывать стиль до длинного рендера / работать самостоятельно'],
],y,[116,CW-116])
y=para('Если горизонталь, длительность или голос уже названы, агент не спрашивает их заново. Решения фиксируются в brief.json; шаблон лежит в templates/. Исходное значение частоты кадров -30fps.',M,y,CW)
callout('Рисованный стиль примеров уже реализован кодом. Пиксельный и toon3D - маршруты для отдельной постановки и теста, а не переключатель готового универсального рига.',y+18)

y=page('03 / Производство','Путь от идеи до MP4')
steps=[
    ('1','Бриф и окружение','Выбрать задачу, проверить инструменты, создать папку нового проекта.'),
    ('2','Идея и понятное начало','Заголовок, конфликт или вопрос, герои, результат для зрителя.'),
    ('3','Реплики и раскладка','Для каждого отрезка: слова, видимое действие, камера, переход и звук.'),
    ('4','Стиль и пробные кадры','Реальные позы, реквизит, пропорции, контакты. Посмотреть крупно.'),
    ('5','Голос и реальные времена','Выбрать роли и голоса, получить запись, alignment и words.json.'),
    ('6','Анимация и камера','Ключевые позы, фазы, промежуточные кадры, реакции и осмысленные планы.'),
    ('7','SFX, музыка и субтитры','Слои по событиям, понятная речь, читаемый синхронный текст.'),
    ('8','Проверка и выдача','Исправить конкретные дефекты. MP4, .blend, код, источники и отчёт.'),
]
for number,title,text in steps:
    c.setFillColor(ACCENT);c.circle(M+14,H-y-13,13,fill=1,stroke=0)
    c.setFillColor(WHITE);c.setFont('NotoBold',10);c.drawCentredString(M+14,H-y-17,number)
    yy=para(title,M+39,y,CW-39,11.2,bold=True)
    yy=para(text,M+39,yy+4,CW-39,9.6)
    y=yy+16
callout('Не ждать финального рендера, чтобы впервые увидеть плечи, кисти и камеру. Сначала проверить короткий фрагмент на настоящих кадрах.',y+5)

y=page('04 / Рисунок','Рука - одна понятная форма')
y=picture(Path('examples/details/resting-hand.png'),y,244)
for text in [
    '<b>Боковое плечо.</b> Внешний контур идёт от плечевого выступа, внутренний начинается у подмышки. Линия от воротника через грудь создаёт ложное крепление руки.',
    '<b>Спокойная поза.</b> Локти около корпуса. Для обычного шага не разводить обе руки широко и не перекрещивать их без причины.',
    '<b>Кисть-варежка.</b> Округлая масса и короткий встроенный большой палец. Это текущий выбор пользователя; отдельные пальцы и ногти не добавляются автоматически.',
    '<b>Цельная цепочка.</b> Плечо, локоть, предплечье, манжета и кисть согласованы. Поворот кисти следует предплечью.'
]:y=bullet(text,y+1)
callout('Другой клиент может выбрать другой стиль. В примерах и профиле автора последним решением остаются простые кисти-варежки.',y+6)

y=page('05 / Реквизит','Разные предметы - разные хваты')
y=picture(Path('examples/details/box-grip.png'),y,188)
y=para('<b>Коробка:</b> ладонь поддерживает дно, короткий большой палец касается переднего угла. Непрозрачная полоса ниже дна не должна перекрывать и разрезать кисть.',M,y,CW,10)+18
y=picture(Path('examples/details/folder-grip.png'),y,188)
y=para('<b>Папка:</b> часть кисти видна снаружи вертикального края, большой палец спереди, общая форма сзади. Манжета входит в ладонь, а не прямо в предмет.',M,y,CW,10)+17
callout('Хват ручки кейса проверяется отдельно: замкнутая форма вокруг перекладины. Уменьшение картинки не заменяет исправления плохого контакта.',y)

y=page('06 / Среда','Пропорции и полезная детализация')
y=picture(Path('examples/stills/02-seated-workspace.png'),y,292)
for text in [
    'Стул виден и действительно поддерживает таз. Под столом есть ноги, стойка кресла, обувь и опора на пол.',
    'Ноутбук или монитор, кофе, книги и мебель соразмерны персонажу. Фонарный столб не становится ростом с собаку.',
    'Помещение узнаётся по назначению: плинтус, панели, крепления, розетки, трубы, фурнитура, полки и инструменты.',
    'Провода, тени и детали заднего плана не проходят поверх ног, лица и кистей без физической причины.'
]:y=bullet(text,y)
callout('Детали нужны для ясности места и масштаба. Не заполнять пустоту случайными объектами, мешающими действию.',y+7)

y=page('07 / Анимация','Движение персонажа - не только зум')
y=table([
    ['Действие','Что проверить в последовательности'],
    ['Ходьба','Контакт, проседание, проход и подъём. Опорная стопа закреплена. Лицо, ботинок и движение направлены в одну сторону.'],
    ['Жест','Рука начинает движение из плеча, локоть и кисть связаны. Предмет остаётся в хвате.'],
    ['Разговор','Уместные реакции, взгляд, моргание, дыхание. Соседний персонаж и робот не стоят неподвижно весь ролик.'],
    ['Предметное действие','Если в реплике падает лифт, в сцене показано падение, а не просто появляется текст.'],
    ['Направления','Цикл отдельно проверен влево и вправо. Нет движения задом наперёд и обратной фазы шага.'],
],y,[105,CW-105])
y=sub('Пробы в наборе',y+4)
y=para('<b>camera-study-9s.mp4:</b> статичные позы и анимированная камера. <b>moving-hold-3s.mp4:</b> два персонажа, дыхание, моргание, повороты головы и жесты. Проба не является циклом ходьбы, липсинком или новым фильмом с озвучкой.',M,y,CW)+18
callout('Фильм по новому сценарию требует своих действий. Не растягивать короткую демонстрацию на нужный хронометраж и не выдавать её за готовую историю.',y)

y=page('08 / Камера','Приближение ради действия')
for path,title,desc in [
    ('examples/camera-keys/two-shot.png','Общий - средний','Сначала пространство, затем внимание к двум героям и их жесту.'),
    ('examples/camera-keys/handle-detail.png','Деталь предмета','Кисть, манжета и ручка кейса. Голова намеренно целиком вне кадра.'),
    ('examples/camera-keys/parcel-closeup.png','Акцент на объекте','Кепка, лицо, обе кисти и коробка остаются в кадре.')]:
    y=picture(Path(path),y,146,width=260,x=M)
    yy=y-154
    para(title,M+277,yy, CW-277,12,bold=True)
    para(desc,M+277,yy+25,CW-277,9.6)
    y+=9
callout('Разгон, торможение и удержания. Проверить начало, середину и конец визуально; границы важных объектов - на каждом кадре. Для второй ориентации сцены перекомпоновываются, а не просто обрезаются.',y)

y=page('09 / Голос и звук','Слышно действие, понятно каждое слово')
y=table([
    ['Слой','Пример'],
    ['Голос','Один или несколько естественных голосов. Сначала короткая проба тембра и произношения.'],
    ['Механизм','Кнопка, дверь, мотор, остановка и сигнал лифта - отдельные события.'],
    ['Атмосфера','При отключении пропадает электрический гул, остаются тишина, скрип и тихий тревожный фон.'],
    ['Музыка','Ниже речи, уходит на важной реплике. Не заполняет каждую паузу.'],
    ['Субтитры','Реальные word timings/alignment, белый текст, небольшой тёмный контур и умеренная тень.'],
],y,[105,CW-105])
y=para('В assets/sfx есть записи дверей и сигнала, десять выбранных UI-эффектов и собственный синтез: мотор, отключение, металлический скрип и напряжение. Три аудиодемо лежат в assets/sfx/demos/. Источники и лицензии - в sources.json.',M,y,CW)+18
y=code(['python scripts/elevenlabs_voice.py --voice-id ID --text-file templates/voice-sample.txt --output output/voice.mp3 --dry-run'],y)
callout('Dry-run не читает ключ и не вызывает API. Для настоящей озвучки нужен свой ELEVENLABS_API_KEY в окружении. Платная генерация здесь не выполнялась.',y+3)

y=page('10 / Режимы','Не смешивать все прошлые требования')
y=sub('Рисованный мультфильм',y)
y=para('Основной готовый пример: плоский мир, нативные меши и кривые, кисти-варежки. Без рекламных плашек и вставок по умолчанию. Новая тема, реклама и персонажи определяются брифом.',M,y,CW)+20
y=sub('Пиксельная графика',y)
y=para('Единая логическая сетка у героя, робота, помещения, эффектов и текста; увеличение nearest-neighbor. Проверка настоящего альфа-канала на светлом и тёмном фоне. Шахматка внутри RGB не считается прозрачностью. Отдельный тест движения и читаемости.',M,y,CW)+20
y=sub('Рекламный или интерфейсный Reels',y)
y=para('Только если выбран такой режим: контрастная карточка, равные отступы, демонстрация сверху и аватар снизу. Субтитры не закрывают лицо и важное действие. Ссылка и обещание рекламы берутся у владельца, а не подставляются из чужого проекта.',M,y,CW)+20
y=sub('Стилизованный3D',y)
y=para('Отдельная сцена, материалы, свет, риг и проба. Не называть плоскую картинку на плоскости полноценной3D-анимацией. В наборе есть скиллы по Blender, но готовый универсальный3D-персонаж не заявлен.',M,y,CW)+20
callout('Научная, новостная и survival-тема требуют проверки фактов. Старый пользовательский PDF - референс постановки и процесса, а не подтверждение любой цифры или рекомендации.',y)

y=page('11 / Скиллы и файлы','Два своих скилла и рабочие примеры')
y=table([
    ['Ресурс','Назначение'],
    ['cartoon-blender-production','Бриф, сценарий, нативный рисунок, камера, звук и выпуск'],
    ['cartoon-visual-qa','Независимое ревью настоящих кадров и движения'],
    ['6 upstream-скиллов','Blender core, animation, asset QA, expert, Grease Pencil и visual gate; полные MIT-лицензии рядом'],
    ['studio/','Код плоских сцен, персонажей, простых кистей и камеры'],
    ['templates/','Нейтральный бриф, сценарий про эхо и восемь планов на48секунд до уточнения по голосу'],
    ['references/user-supplied/','Два исходных PDF, прежние промпты и идеи сюжетов'],
],y,[165,CW-165])
y=para('Скиллы можно читать прямо из папки. Для отдельной установки используйте scripts/install_skills.py с явным --dest. Код и ассеты остаются в корне набора; путь можно сохранить в CARTOON_KIT_ROOT.',M,y,CW)+18
callout('Никаких чужих API-ключей, обещаний бесплатных кредитов или скрытого подключения MCP. Настройка и источники описаны в docs/.',y)

y=page('12 / Проверка и выдача','Что должно быть перед отправкой')
for text in [
    '<b>Рисунок:</b> плечи сбоку, кисти цельные, опора ног/таза и контакт с предметами понятны. Масштаб согласован.',
    '<b>Движение:</b> нет скольжения, обратной ходьбы, мигания и внезапных перекрытий. Реагируют все участники сцены.',
    '<b>Камера:</b> головы, активные руки и предметы не теряются. Крупные планы осмысленны.',
    '<b>Текст:</b> читается на телефоне, соответствует аудио, не закрывает действие. Карточки контрастны и имеют равные поля.',
    '<b>Звук:</b> речь ясная, SFX синхронны, нет клиппинга и резких нежелательных пиков.',
    '<b>Экспорт:</b> реальные разрешение, fps и длительность подтверждены. Нет бессмысленных чёрных или пустых кадров.',
    '<b>Проект:</b> есть MP4, редактируемые .blend, код, звук/таймкоды, источники и честное описание ограничений.'
]:y=bullet(text,y)
y=callout('Кодовая проверка координат и ответ ревьюера не заменяют просмотр. Если пользователь нашёл проблему, исправляется результат, а не формулировка отчёта.',y+4)
y=para('Проверки именно этой сборки - в VALIDATION.md. Новый компьютер должен пройти doctor и пробный рендер заново. Установка Blender MCP и реальные запросы ElevenLabs не считаются выполненными только потому, что инструкции лежат в папке.',M,y,CW,9.5)

assert PAGE==13
c.save()
print(PDF)
