import socketio
from aiohttp import web
import asyncio
import random
import time
import os

sio = socketio.AsyncServer(cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

connected_players = {}
ready_players = set()
frozen_players = set()
punishments_list = []
used_punishments = []
player_answers = {}
question_number = 0
final_punishment_data = {}  # تغيير من متغير واحد إلى قاموس
surprise_ready = {}
final_losers = []  # قائمة بجميع الخاسرين النهائيين

questions_bank = [
    # الأسئلة الأصلية
    {"question": "ما هي عاصمة فرنسا؟", "options": ["باريس", "روما", "مدريد", "برلين"], "correct": "باريس"},
    {"question": "ما هو أكبر كوكب في المجموعة الشمسية؟", "options": ["المريخ", "زحل", "الأرض", "المشتري"], "correct": "المشتري"},
    {"question": "كم عدد أيام السنة الكبيسة؟", "options": ["365", "366", "364", "367"], "correct": "366"},
    {"question": "من اخترع المصباح الكهربائي؟", "options": ["أديسون", "نيوتن", "أينشتاين", "بيل"], "correct": "أديسون"},
    {"question": "ما البحر الذي يطل على السعودية؟", "options": ["الأحمر", "المتوسط", "العربي", "الكاريبي"], "correct": "الأحمر"},
    
    # أسئلة جغرافية مبسطة
    {"question": "ما هي عاصمة مصر؟", "options": ["القاهرة", "الرياض", "دبي", "بيروت"], "correct": "القاهرة"},
    {"question": "ما هي أكبر دولة عربية من حيث المساحة؟", "options": ["مصر", "السعودية", "الجزائر", "السودان"], "correct": "الجزائر"},
    {"question": "أي قارة توجد فيها أستراليا؟", "options": ["آسيا", "أمريكا", "أوروبا", "أوقيانوسيا"], "correct": "أوقيانوسيا"},
    {"question": "ما هي عاصمة السعودية؟", "options": ["جدة", "الرياض", "مكة", "المدينة"], "correct": "الرياض"},
    {"question": "ما هو أطول نهر في العالم؟", "options": ["النيل", "الأمازون", "المسيسيبي", "دجلة"], "correct": "النيل"},
    {"question": "في أي دولة توجد مدينة جدة؟", "options": ["مصر", "الإمارات", "السعودية", "الكويت"], "correct": "السعودية"},
    {"question": "أي مدينة هي عاصمة الإمارات العربية المتحدة؟", "options": ["دبي", "الشارقة", "أبوظبي", "عجمان"], "correct": "أبوظبي"},
    {"question": "ما هي أكبر دولة في العالم من حيث المساحة؟", "options": ["الصين", "كندا", "الولايات المتحدة", "روسيا"], "correct": "روسيا"},
    
    # أسئلة عامة بسيطة
    {"question": "ما هو لون السماء في النهار؟", "options": ["أزرق", "أحمر", "أخضر", "أصفر"], "correct": "أزرق"},
    {"question": "كم يوم في الأسبوع؟", "options": ["5", "6", "7", "8"], "correct": "7"},
    {"question": "ما هو الحيوان الذي له خرطوم طويل؟", "options": ["الزرافة", "الفيل", "الأسد", "النمر"], "correct": "الفيل"},
    {"question": "كم ساعة في اليوم؟", "options": ["12", "18", "24", "36"], "correct": "24"},
    {"question": "أي من هذه الفواكه حمراء عادةً؟", "options": ["التفاح", "الموز", "البرتقال", "الكيوي"], "correct": "التفاح"},
    {"question": "ما هو المعدن الذي يستخدم في صناعة العملات المعدنية غالباً؟", "options": ["الذهب", "الحديد", "النحاس", "الفضة"], "correct": "النحاس"},
    {"question": "ما هو عدد أرجل العنكبوت؟", "options": ["4", "6", "8", "10"], "correct": "8"},
    {"question": "ما عدد شهور السنة؟", "options": ["10", "11", "12", "13"], "correct": "12"},
    
    # أسئلة رياضية بسيطة
    {"question": "كم عدد لاعبي فريق كرة القدم على أرض الملعب؟", "options": ["9", "10", "11", "12"], "correct": "11"},
    {"question": "ما هي الرياضة التي تلعب بالمضرب والريشة؟", "options": ["التنس", "كرة الطاولة", "الريشة الطائرة", "الاسكواش"], "correct": "الريشة الطائرة"},
    {"question": "أي دولة فازت بكأس العالم لكرة القدم 2022؟", "options": ["البرازيل", "فرنسا", "الأرجنتين", "إنجلترا"], "correct": "الأرجنتين"},
    {"question": "ما هي الرياضة التي يسجل فيها هدف في مرمى؟", "options": ["كرة القدم", "كرة السلة", "التنس", "الجولف"], "correct": "كرة القدم"},
    {"question": "كم نقطة يحصل عليها الفريق عند تسجيل هدف في كرة القدم؟", "options": ["1", "2", "3", "5"], "correct": "1"},
    {"question": "من هو اللاعب المشهور بلقب (الأسطورة) في كرة القدم؟", "options": ["ميسي", "رونالدو", "بيليه", "مارادونا"], "correct": "بيليه"},
    {"question": "ما هي الرياضة التي تلعب في الماء؟", "options": ["كرة اليد", "كرة السلة", "كرة الماء", "كرة الطائرة"], "correct": "كرة الماء"},
    {"question": "أي من هذه الرياضات لا تستخدم الكرة؟", "options": ["كرة القدم", "كرة السلة", "السباحة", "كرة اليد"], "correct": "السباحة"},
    
    # أسئلة عن الطعام
    {"question": "ما هو طعام يابان الشهير المصنوع من الأرز والسمك؟", "options": ["البيتزا", "البرغر", "السوشي", "الكبسة"], "correct": "السوشي"},
    {"question": "ما هي الفاكهة المعروفة بـ 'ملك الفواكه'؟", "options": ["التفاح", "الموز", "المانجو", "الدوريان"], "correct": "الدوريان"},
    {"question": "أي من هذه المشروبات يحتوي على الكافيين؟", "options": ["عصير البرتقال", "الحليب", "القهوة", "الليمون"], "correct": "القهوة"},
    {"question": "ما هو الطبق السعودي الشهير المصنوع من الأرز واللحم؟", "options": ["المندي", "الكبسة", "المقلوبة", "البرياني"], "correct": "الكبسة"},
    {"question": "ما هي الخضار الحمراء التي تستخدم في صلصة المعكرونة؟", "options": ["الخيار", "الطماطم", "الباذنجان", "الجزر"], "correct": "الطماطم"},
    {"question": "ما هو نوع الطعام الذي تشتهر به إيطاليا؟", "options": ["السوشي", "الباستا", "الكبسة", "الكاري"], "correct": "الباستا"},
    {"question": "أي من هذه المأكولات يصنع أساسًا من الحليب؟", "options": ["الخبز", "الجبن", "البطاطس", "الأرز"], "correct": "الجبن"},
    {"question": "ما هي المادة التي تجعل الخبز ينتفخ؟", "options": ["السكر", "الملح", "الخميرة", "الماء"], "correct": "الخميرة"},
    
    # أسئلة عن الحيوانات
    {"question": "ما هو الحيوان الذي له أذنان طويلتان ويأكل الجزر؟", "options": ["القط", "الكلب", "الأرنب", "الفأر"], "correct": "الأرنب"},
    {"question": "ما هو أسرع حيوان في العالم؟", "options": ["النمر", "الفهد", "الأسد", "الغزال"], "correct": "الفهد"},
    {"question": "أي من هذه الحيوانات يعيش في الماء؟", "options": ["الأسد", "الفيل", "الجمل", "الحوت"], "correct": "الحوت"},
    {"question": "ما هو الطائر الذي لا يطير؟", "options": ["النسر", "البطريق", "الحمام", "البط"], "correct": "البطريق"},
    {"question": "ما هو الحيوان الذي له قرون ويعطي الحليب؟", "options": ["الأسد", "البقرة", "الكلب", "الفأر"], "correct": "البقرة"},
    {"question": "ما هو صوت القط؟", "options": ["نباح", "مواء", "خوار", "نهيق"], "correct": "مواء"},
    {"question": "ما هو الحيوان الأكبر في العالم؟", "options": ["الفيل", "الزرافة", "الحوت الأزرق", "وحيد القرن"], "correct": "الحوت الأزرق"},
    {"question": "أي من هذه الحيوانات يمكنه الطيران؟", "options": ["البطريق", "النعامة", "الدجاجة", "الخفاش"], "correct": "الخفاش"},
    
    # أسئلة عن وسائل النقل
    {"question": "ما هي وسيلة النقل التي تسير على السكك الحديدية؟", "options": ["السيارة", "الطائرة", "القطار", "الدراجة"], "correct": "القطار"},
    {"question": "ما هي وسيلة النقل التي تطير في السماء؟", "options": ["السيارة", "الطائرة", "القارب", "الدراجة"], "correct": "الطائرة"},
    {"question": "ما هي وسيلة النقل التي لها عجلتان؟", "options": ["السيارة", "الشاحنة", "الحافلة", "الدراجة"], "correct": "الدراجة"},
    {"question": "ما هي وسيلة النقل التي تستخدم في البحر؟", "options": ["السيارة", "الطائرة", "القارب", "الدراجة"], "correct": "القارب"},
    {"question": "أي من وسائل النقل التالية هي الأسرع؟", "options": ["السيارة", "الطائرة", "القطار", "الحافلة"], "correct": "الطائرة"},
    {"question": "ما هي وسيلة النقل التي تعمل بالكهرباء غالباً؟", "options": ["الترام", "الطائرة", "السفينة", "الدراجة"], "correct": "الترام"},
    {"question": "ما هو المكان المخصص لهبوط وإقلاع الطائرات؟", "options": ["الميناء", "المطار", "محطة القطار", "موقف الباصات"], "correct": "المطار"},
    {"question": "ما هي وسيلة النقل التي تحمل الكثير من الركاب في المدينة؟", "options": ["الدراجة", "السيارة", "الحافلة", "الشاحنة"], "correct": "الحافلة"},
    
    # أسئلة عن الألوان
    {"question": "ما هو اللون الناتج عن خلط الأزرق والأصفر؟", "options": ["أحمر", "أخضر", "برتقالي", "بنفسجي"], "correct": "أخضر"},
    {"question": "ما هو لون علم المملكة العربية السعودية؟", "options": ["أخضر", "أحمر", "أزرق", "أصفر"], "correct": "أخضر"},
    {"question": "ما هو لون الطماطم الناضجة؟", "options": ["أخضر", "أحمر", "أصفر", "برتقالي"], "correct": "أحمر"},
    {"question": "ما هو اللون الناتج عن خلط الأحمر والأصفر؟", "options": ["أرجواني", "أزرق", "برتقالي", "أخضر"], "correct": "برتقالي"},
    {"question": "ما هو لون الموز الناضج؟", "options": ["أخضر", "أحمر", "أصفر", "برتقالي"], "correct": "أصفر"},
    {"question": "ما هو لون السماء صافية في النهار؟", "options": ["رمادي", "أزرق", "أبيض", "أسود"], "correct": "أزرق"},
    {"question": "ما هو لون الثلج؟", "options": ["أبيض", "أزرق", "شفاف", "رمادي"], "correct": "أبيض"},
    {"question": "ما هو لون العشب؟", "options": ["أصفر", "أحمر", "أزرق", "أخضر"], "correct": "أخضر"},
    
    # أسئلة عن المهن
    {"question": "من يعالج المرضى في المستشفى؟", "options": ["المعلم", "الطبيب", "المهندس", "الطيار"], "correct": "الطبيب"},
    {"question": "من يعلم الطلاب في المدرسة؟", "options": ["المعلم", "الطبيب", "الشرطي", "المهندس"], "correct": "المعلم"},
    {"question": "من يصمم المباني والجسور؟", "options": ["المعلم", "الطبيب", "المهندس", "الطيار"], "correct": "المهندس"},
    {"question": "من يقود الطائرة؟", "options": ["المعلم", "السائق", "المهندس", "الطيار"], "correct": "الطيار"},
    {"question": "من يطفئ الحرائق؟", "options": ["الطبيب", "رجل الإطفاء", "الشرطي", "المعلم"], "correct": "رجل الإطفاء"},
    {"question": "من يخبز الخبز؟", "options": ["الجزار", "الخباز", "الطباخ", "البقال"], "correct": "الخباز"},
    {"question": "من يزرع المحاصيل في الحقول؟", "options": ["المزارع", "الصياد", "الطبيب", "المهندس"], "correct": "المزارع"},
    {"question": "من يحافظ على الأمن ويمنع الجريمة؟", "options": ["المعلم", "الطبيب", "الشرطي", "الطيار"], "correct": "الشرطي"},
    
    # أسئلة عن أجزاء الجسم
    {"question": "ما هو العضو المسؤول عن التنفس في جسم الإنسان؟", "options": ["القلب", "الرئتان", "الكبد", "المعدة"], "correct": "الرئتان"},
    {"question": "ما هو العضو المسؤول عن ضخ الدم في جسم الإنسان؟", "options": ["القلب", "الرئتان", "الكبد", "المعدة"], "correct": "القلب"},
    {"question": "ما هو العضو الذي نستخدمه للنظر؟", "options": ["الأذن", "الأنف", "العين", "اللسان"], "correct": "العين"},
    {"question": "ما هو العضو الذي نستخدمه للسمع؟", "options": ["العين", "الأنف", "الأذن", "اللسان"], "correct": "الأذن"},
    {"question": "كم عدد أصابع اليد الواحدة؟", "options": ["3", "4", "5", "6"], "correct": "5"},
    {"question": "ما هو العضو المسؤول عن تذوق الطعام؟", "options": ["الأنف", "العين", "الشفاه", "اللسان"], "correct": "اللسان"},
    {"question": "ما هو العضو المسؤول عن الشم؟", "options": ["الأذن", "الأنف", "العين", "اللسان"], "correct": "الأنف"},
    {"question": "ما هو العظم الموجود في الرأس لحماية الدماغ؟", "options": ["الجمجمة", "العمود الفقري", "الفخذ", "الساعد"], "correct": "الجمجمة"}
]

# --- Static File Handlers ---
async def index(request): return web.FileResponse('./frontend/index.html')
async def player_page(request): return web.FileResponse('./frontend/players.html')
async def manager_page(request): return web.FileResponse('./frontend/manager.html')
async def static_file(request):
    filename = request.match_info.get('filename')
    return web.FileResponse(os.path.join('./frontend', filename))

app.router.add_get('/', index)
app.router.add_get('/player', player_page)
app.router.add_get('/manager', manager_page)
app.router.add_get('/static/{filename}', static_file)

# --- Socket Events ---
@sio.event
async def connect(sid, environ):
    print(f"✅ اتصال: {sid}")

@sio.event
async def register_name(sid, name):
    connected_players[sid] = {"name": name, "score": 0}
    await sio.emit("new_player", {"name": name})

@sio.event
async def confirm_ready(sid):
    ready_players.add(sid)
    if ready_players == set(connected_players):
        await sio.emit("registration_completed")
        await sio.emit("play_start_sound")

@sio.event
async def selected_punishments(sid, data):
    global punishments_list, used_punishments
    punishments_list = data
    used_punishments = []

@sio.event
async def answer(sid, data):
    if sid in frozen_players or sid not in player_answers:
        return
    answer = data.get("answer")
    question_index = data.get("question_index")
    if answer is None or question_index is None:
        return
    try:
        question_index = int(question_index)
        answers = player_answers[sid]["answers"]
        if len(answers) <= question_index:
            answers.extend([None] * (question_index - len(answers) + 1))
        answers[question_index] = (answer, time.time())
    except Exception as e:
        print(f"خطأ في answer: {e}")

@sio.event
async def freeze_player(sid, target_name):
    for target_sid, info in connected_players.items():
        if info['name'] == target_name:
            frozen_players.add(target_sid)
            await sio.emit("player_frozen", {"by": connected_players[sid]['name']}, room=target_sid)
            break

@sio.event
async def start_game_signal(sid):
    asyncio.create_task(start_elimination_game())

@sio.event
async def surprise_choice(sid, data):
    if sid not in surprise_ready:
        return
    surprise_ready[sid] = data['type']
    active_names = [info['name'] for s, info in connected_players.items() if s != sid and s not in frozen_players and s in player_answers]
    await sio.emit("choose_target_player", {"surprise_type": data['type'], "players": active_names}, room=sid)

@sio.event
async def surprise_target_selected(sid, data):
    surprise_type = surprise_ready.get(sid)
    if not surprise_type:
        return
    del surprise_ready[sid]
    target_sid = next((s for s, info in connected_players.items() if info['name'] == data['target']), None)
    if not target_sid:
        return
    if surprise_type == "freeze":
        frozen_players.add(target_sid)
        await sio.emit("player_frozen", {"by": connected_players[sid]['name']}, room=target_sid)
    elif surprise_type == "steal":
        stolen = min(4, connected_players[target_sid]['score'])
        connected_players[sid]['score'] += stolen
        connected_players[target_sid]['score'] -= stolen
        await sio.emit("points_stolen", {"from": connected_players[target_sid]['name'], "to": connected_players[sid]['name'], "amount": stolen})
    elif surprise_type == "swap":
        connected_players[sid]['score'], connected_players[target_sid]['score'] = connected_players[target_sid]['score'], connected_players[sid]['score']
        await sio.emit("points_swapped", {"with": connected_players[target_sid]['name']}, room=sid)
        await sio.emit("points_swapped", {"with": connected_players[sid]['name']}, room=target_sid)
    await update_leaderboard()

@sio.event
async def replay_crown(sid):
    if sid in connected_players:
        await sio.emit("crown_winner", {"name": connected_players[sid]['name']})

@sio.event
async def i_am_final_winner(sid):
    # إعداد بيانات المرحلة النهائية
    all_losers = [info['name'] for s, info in connected_players.items() 
                 if s != sid and s in ready_players]
    
    await sio.emit("final_stage_start", {
        "players": all_losers,
        "punishments": punishments_list
    }, room=sid)

@sio.event
async def set_final_loser(sid, data):
    global final_losers
    loser = data.get("loser")
    
    # إضافة الخاسر للقائمة إذا لم يكن موجوداً بالفعل
    if loser and loser not in final_losers:
        final_losers.append(loser)
    
    await sio.emit("final_loser_selected", {"loser": loser})

@sio.event
async def final_apply_punishment(sid, data):
    loser = data.get("loser")
    punishment = data.get("punishment")
    
    if not loser or not punishment:
        return
    
    # تخزين العقوبة النهائية في القاموس
    final_punishment_data[loser] = punishment
    
    # إرسال التحديث إلى جميع اللاعبين
    await sio.emit("final_punishment", {
        "loser": loser,
        "punishment": punishment
    })

@sio.event
async def apply_all_punishments(sid, data):
    punishments = data.get("punishments", [])
    for item in punishments:
        loser = item.get("loser")
        punishment = item.get("punishment")
        if loser and punishment:
            final_punishment_data[loser] = punishment
            await sio.emit("final_punishment", {
                "loser": loser,
                "punishment": punishment
            })
    
    # إرسال تأكيد تطبيق جميع العقوبات
    await sio.emit("all_punishments_applied")

@sio.event
async def spin_flash_punishments(sid):
    # تحديث دالة تدوير العقوبات لتعمل مع النظام الجديد
    remaining = [p for p in punishments_list if p not in used_punishments]
    if not remaining:
        return
    
    random_punishments = random.sample(remaining, min(len(remaining), 5))
    await sio.emit("flash_punishments", {
        "punishments": random_punishments
    }, room=sid)

# --- Internal Functions ---
async def update_leaderboard():
    leaderboard = sorted([
        {"name": info['name'], "score": info['score']} for info in connected_players.values()
    ], key=lambda x: -x['score'])
    await sio.emit("leaderboard_update", leaderboard)
    await sio.emit("leaderboard_chart", leaderboard)

async def start_elimination_game():
    global question_number, frozen_players, player_answers, final_punishment_data, final_losers
    await asyncio.sleep(13.05)
    await sio.emit("registration_ended")
    await asyncio.sleep(4)

    active_players = list(ready_players)
    eliminated_players = []  # لتتبع اللاعبين الذين خرجوا من اللعبة
    
    while len(active_players) > 1:
        question_number += 1
        await sio.emit("question_number", question_number)
        await sio.emit("play_round_sound")
        await sio.emit("start_countdown", {"duration": 15})

        round_questions = random.sample(questions_bank, 4)
        player_answers = {sid: {"answers": []} for sid in active_players}

        for sid in active_players:
            await sio.emit("round_questions", round_questions, room=sid)

        await asyncio.sleep(15.5)

        correct = [q['correct'] for q in round_questions]
        scored = []

        for sid in active_players:
            answers = player_answers[sid]["answers"]
            correct_count = 0
            total_time = 0
            for i in range(4):
                if i < len(answers) and answers[i] and answers[i][0] == correct[i]:
                    correct_count += 1
                    total_time += answers[i][1]
                else:
                    total_time += time.time()
            connected_players[sid]['score'] += correct_count
            scored.append((sid, correct_count, total_time))

        scored.sort(key=lambda x: (-x[1], x[2]))
        await update_leaderboard()

        loser_sid = scored[-1][0]
        await sio.emit("you_lost", room=loser_sid)
        active_players.remove(loser_sid)
        eliminated_players.append(loser_sid)  # إضافة اللاعب إلى قائمة الخاسرين

        await asyncio.sleep(5)

        winner_sid, winner_correct, winner_time = scored[0]
        perfect = winner_correct == 4

        await sio.emit("you_won", {
            "name": connected_players[winner_sid]['name'],
            "score": connected_players[winner_sid]['score'],
            "perfect": perfect,
            "fastest": True
        }, room=winner_sid)

        if perfect and len(active_players) > 1:
            await sio.emit("show_surprise_box", room=winner_sid)
            await sio.emit("play_alarm_sound")
            surprise_ready[winner_sid] = True
            await asyncio.sleep(6)

        await sio.emit("ask_to_freeze", {
            "players": [connected_players[s]['name'] for s in active_players if s != winner_sid]
        }, room=winner_sid)

        frozen_players.clear()
        await asyncio.sleep(6)
        await sio.emit("unfreeze_all")

    if active_players:
        final_sid = active_players[0]
        winner_name = connected_players[final_sid]['name']
        
        # إعداد قائمة الخاسرين النهائية
        final_losers = [connected_players[s]['name'] for s in eliminated_players]
        
        await sio.emit("final_winner", winner_name)
        await sio.emit("crown_winner", {"name": winner_name})
        
        # إرسال بيانات المرحلة النهائية للفائز
        await sio.emit("final_stage_start", {
            "players": final_losers,
            "punishments": punishments_list
        }, room=final_sid)

# --- Run App ---
if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)