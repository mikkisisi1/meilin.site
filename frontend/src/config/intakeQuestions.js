// Weight-loss intake questionnaire — localized for all UI languages.
// type: 'single' | 'single_custom' | 'multi' | 'multi_custom' | 'data'
//
// We keep `id` and answer-key strings (q5/q8 conditionals) language-stable so
// skipIf logic and the [АНКЕТА] summary stay consistent across switches.

const Q = (lang) => INTAKE_BY_LANG[lang] || INTAKE_BY_LANG.en;

const SKIP_NEVER_TRIED = (a) => /never/i.test(a.q5_key || '');
const SKIP_NO_OVEREATING = (a) => a.q8_key === 'no';

const INTAKE_BY_LANG = {
  en: {
    questions: [
      { id: 'q2', text: 'Are you looking to lose weight for yourself or to help a loved one?', type: 'single', options: ['For myself', 'For a loved one'] },
      { id: 'q3', text: 'How many kilograms would you like to lose?', type: 'single', options: ['Up to 5 kg', '5–10 kg', '10–20 kg', 'More than 20 kg'] },
      { id: 'q4', text: 'Tell me a bit about yourself:', type: 'data', fields: [
        { key: 'age', label: 'Age' },
        { key: 'weight', label: 'Current weight (kg)' },
        { key: 'height', label: 'Height (cm)' },
      ] },
      { id: 'q5', text: 'Have you successfully lost weight before?', type: 'single', options: ['Yes, it worked', 'I tried, but no result', "I've never tried"], keys: ['yes', 'tried', 'never'] },
      { id: 'q6', text: 'If yes — did the weight come back?', type: 'single_custom', options: ['Yes, all of it returned', 'Some returned', 'It stayed off'], skipIf: SKIP_NEVER_TRIED },
      { id: 'q7', text: 'How is your weight changing right now?', type: 'single_custom', options: ['Slowly increasing', 'Staying the same', 'Goes up and down'] },
      { id: 'q8', text: 'Is it sometimes hard to stop eating?', type: 'single', options: ['Yes, often', 'Sometimes', 'Rarely', 'No'], keys: ['often', 'sometimes', 'rarely', 'no'] },
      { id: 'q9', text: 'When does it most often happen?', type: 'single_custom', options: ['Morning', 'Afternoon', 'Evening', 'Night'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q10', text: 'What usually triggers overeating?', type: 'multi_custom', options: ['Tiredness', 'Stress', 'Boredom', 'Just habit', 'Social/festive meals'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q11', text: 'How active are you physically?', type: 'single', options: ['Almost no movement', 'Light (walks)', 'Moderate (3–4×/week)', 'High (regular sport)'] },
      { id: 'q12', text: 'How is your sleep?', type: 'single_custom', options: ['Less than 6 hours', '6–7 hours', '7–8 hours'] },
      { id: 'q13', text: 'Any health limitations? (multiple allowed)', type: 'multi_custom', options: ['Blood pressure', 'Diabetes', 'Thyroid', 'Joints', 'Heart', 'No limitations'] },
      { id: 'q14', text: 'How important is it to solve this now?', type: 'single', options: ['1–3: Just looking', '4–6: Want to, not urgent', '7–8: Important, ready to act', '9–10: Top priority'] },
    ],
    intro: (name) => `Nice to meet you, ${name}! To work right away with your situation, I’ll ask a few short questions. It will take 2–3 minutes.`,
    outro: (name) => `Thank you, ${name}. The picture is clear. Now tell me in your own words — what is happening now and what have you tried before?`,
    next: 'Next', done: 'Done', custom: 'Other...',
    field_age: 'Age', field_weight: 'Weight (kg)', field_height: 'Height (cm)',
    summary_label: 'INTAKE',
  },
  ru: {
    questions: [
      { id: 'q2', text: 'Вы хотите снизить вес для себя или помочь кому-то из близких?', type: 'single', options: ['Для себя', 'Для близкого человека'] },
      { id: 'q3', text: 'На сколько килограмм хотите снизить?', type: 'single', options: ['До 5 кг', '5–10 кг', '10–20 кг', 'Более 20 кг'] },
      { id: 'q4', text: 'Укажите ваши данные:', type: 'data', fields: [
        { key: 'age', label: 'Возраст' },
        { key: 'weight', label: 'Вес сейчас (кг)' },
        { key: 'height', label: 'Рост (см)' },
      ] },
      { id: 'q5', text: 'Раньше удавалось снижать вес?', type: 'single', options: ['Да, получалось', 'Пробовал(а), но без результата', 'Никогда не пробовал(а)'], keys: ['yes', 'tried', 'never'] },
      { id: 'q6', text: 'Если да — вес потом возвращался?', type: 'single_custom', options: ['Да, возвращался весь', 'Возвращалась часть', 'Держался долго'], skipIf: SKIP_NEVER_TRIED },
      { id: 'q7', text: 'Как сейчас меняется ваш вес?', type: 'single_custom', options: ['Постепенно растёт', 'Стоит на месте', 'Гуляет туда-сюда'] },
      { id: 'q8', text: 'Бывает сложно остановиться в еде?', type: 'single', options: ['Да, часто', 'Иногда', 'Редко', 'Нет'], keys: ['often', 'sometimes', 'rarely', 'no'] },
      { id: 'q9', text: 'Когда это чаще всего происходит?', type: 'single_custom', options: ['Утром', 'Днём', 'Вечером', 'Ночью'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q10', text: 'Что обычно запускает переедание?', type: 'multi_custom', options: ['Усталость', 'Стресс', 'Скука', 'Просто привычка', 'Компания/застолье'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q11', text: 'Уровень физической активности?', type: 'single', options: ['Почти нет движения', 'Лёгкая активность (прогулки)', 'Умеренная (3–4 раза в неделю)', 'Высокая (спорт регулярно)'] },
      { id: 'q12', text: 'Как со сном?', type: 'single_custom', options: ['Сплю меньше 6 часов', '6–7 часов', '7–8 часов'] },
      { id: 'q13', text: 'Есть ли ограничения по здоровью? (можно выбрать несколько)', type: 'multi_custom', options: ['Давление', 'Сахарный диабет', 'Щитовидная железа', 'Суставы', 'Сердце', 'Нет ограничений'] },
      { id: 'q14', text: 'Насколько важно решить это сейчас?', type: 'single', options: ['1–3: Пока просто смотрю', '4–6: Хочу, но не горит', '7–8: Важно, готов(а) действовать', '9–10: Приоритет номер один'] },
    ],
    intro: (name) => `Приятно познакомиться, ${name}! Чтобы сразу работать точно под вашу ситуацию, задам несколько коротких вопросов. Это займёт 2–3 минуты.`,
    outro: (name) => `Спасибо, ${name}. Картина понятна. Теперь расскажите своими словами — что сейчас происходит и что пробовали раньше?`,
    next: 'Далее', done: 'Готово', custom: 'Свой вариант...',
    field_age: 'Возраст', field_weight: 'Вес (кг)', field_height: 'Рост (см)',
    summary_label: 'АНКЕТА',
  },
  es: {
    questions: [
      { id: 'q2', text: '¿Quieres bajar de peso para ti o para ayudar a un ser querido?', type: 'single', options: ['Para mí', 'Para un ser querido'] },
      { id: 'q3', text: '¿Cuántos kilos quieres bajar?', type: 'single', options: ['Hasta 5 kg', '5–10 kg', '10–20 kg', 'Más de 20 kg'] },
      { id: 'q4', text: 'Cuéntame un poco sobre ti:', type: 'data', fields: [
        { key: 'age', label: 'Edad' },
        { key: 'weight', label: 'Peso actual (kg)' },
        { key: 'height', label: 'Altura (cm)' },
      ] },
      { id: 'q5', text: '¿Has logrado bajar de peso antes?', type: 'single', options: ['Sí, funcionó', 'Lo intenté, sin resultado', 'Nunca lo he intentado'], keys: ['yes', 'tried', 'never'] },
      { id: 'q6', text: 'Si sí — ¿el peso volvió?', type: 'single_custom', options: ['Sí, todo volvió', 'Volvió parte', 'Se mantuvo'], skipIf: SKIP_NEVER_TRIED },
      { id: 'q7', text: '¿Cómo cambia tu peso ahora?', type: 'single_custom', options: ['Sube poco a poco', 'Está estable', 'Sube y baja'] },
      { id: 'q8', text: '¿A veces es difícil parar de comer?', type: 'single', options: ['Sí, a menudo', 'A veces', 'Rara vez', 'No'], keys: ['often', 'sometimes', 'rarely', 'no'] },
      { id: 'q9', text: '¿Cuándo ocurre con más frecuencia?', type: 'single_custom', options: ['Mañana', 'Tarde', 'Noche', 'Madrugada'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q10', text: '¿Qué suele desencadenarlo?', type: 'multi_custom', options: ['Cansancio', 'Estrés', 'Aburrimiento', 'Hábito', 'Reuniones/festividades'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q11', text: 'Nivel de actividad física:', type: 'single', options: ['Casi no me muevo', 'Ligera (caminatas)', 'Moderada (3–4×/sem)', 'Alta (deporte regular)'] },
      { id: 'q12', text: '¿Cómo duermes?', type: 'single_custom', options: ['Menos de 6 horas', '6–7 horas', '7–8 horas'] },
      { id: 'q13', text: '¿Limitaciones de salud? (varias)', type: 'multi_custom', options: ['Presión', 'Diabetes', 'Tiroides', 'Articulaciones', 'Corazón', 'Sin limitaciones'] },
      { id: 'q14', text: '¿Qué tan importante es resolverlo ahora?', type: 'single', options: ['1–3: Solo mirando', '4–6: Quiero, no urge', '7–8: Listo para actuar', '9–10: Prioridad #1'] },
    ],
    intro: (name) => `Encantado de conocerte, ${name}. Para trabajar exactamente en tu situación, te haré unas preguntas cortas. Tomará 2–3 minutos.`,
    outro: (name) => `Gracias, ${name}. El cuadro está claro. Ahora cuéntame con tus palabras: ¿qué pasa ahora y qué has probado antes?`,
    next: 'Siguiente', done: 'Listo', custom: 'Otro...',
    field_age: 'Edad', field_weight: 'Peso (kg)', field_height: 'Altura (cm)',
    summary_label: 'CUESTIONARIO',
  },
  fr: {
    questions: [
      { id: 'q2', text: 'Souhaitez-vous perdre du poids pour vous-même ou aider un proche ?', type: 'single', options: ['Pour moi', 'Pour un proche'] },
      { id: 'q3', text: 'Combien de kilos souhaitez-vous perdre ?', type: 'single', options: ["Jusqu'à 5 kg", '5–10 kg', '10–20 kg', 'Plus de 20 kg'] },
      { id: 'q4', text: 'Parlez-moi un peu de vous :', type: 'data', fields: [
        { key: 'age', label: 'Âge' },
        { key: 'weight', label: 'Poids actuel (kg)' },
        { key: 'height', label: 'Taille (cm)' },
      ] },
      { id: 'q5', text: 'Avez-vous déjà réussi à perdre du poids ?', type: 'single', options: ['Oui, ça a marché', "J'ai essayé, sans résultat", "Je n'ai jamais essayé"], keys: ['yes', 'tried', 'never'] },
      { id: 'q6', text: 'Si oui — le poids est-il revenu ?', type: 'single_custom', options: ['Oui, tout est revenu', "Une partie est revenue", 'Le poids est resté stable'], skipIf: SKIP_NEVER_TRIED },
      { id: 'q7', text: 'Comment évolue votre poids actuellement ?', type: 'single_custom', options: ['Augmente lentement', 'Stable', 'Variable'] },
      { id: 'q8', text: 'Avez-vous parfois du mal à arrêter de manger ?', type: 'single', options: ['Oui, souvent', 'Parfois', 'Rarement', 'Non'], keys: ['often', 'sometimes', 'rarely', 'no'] },
      { id: 'q9', text: 'Quand cela arrive-t-il le plus souvent ?', type: 'single_custom', options: ['Matin', 'Après-midi', 'Soir', 'Nuit'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q10', text: 'Quels sont les déclencheurs ?', type: 'multi_custom', options: ['Fatigue', 'Stress', 'Ennui', 'Habitude', 'Repas en société'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q11', text: 'Niveau d’activité physique :', type: 'single', options: ['Très peu', 'Légère (marches)', 'Modérée (3–4×/sem)', 'Élevée (sport régulier)'] },
      { id: 'q12', text: 'Et le sommeil ?', type: 'single_custom', options: ['Moins de 6 h', '6–7 h', '7–8 h'] },
      { id: 'q13', text: 'Limitations de santé ? (plusieurs possibles)', type: 'multi_custom', options: ['Tension', 'Diabète', 'Thyroïde', 'Articulations', 'Cœur', 'Aucune'] },
      { id: 'q14', text: 'Importance de régler cela maintenant ?', type: 'single', options: ['1–3 : Je regarde', '4–6 : Envie, pas urgent', '7–8 : Important, prêt(e)', '9–10 : Priorité absolue'] },
    ],
    intro: (name) => `Ravi de vous rencontrer, ${name}. Pour travailler précisément sur votre situation, je vais poser quelques questions courtes. 2 à 3 minutes.`,
    outro: (name) => `Merci, ${name}. Le tableau est clair. Maintenant racontez-moi avec vos mots — que se passe-t-il et qu'avez-vous déjà essayé ?`,
    next: 'Suivant', done: 'Terminé', custom: 'Autre...',
    field_age: 'Âge', field_weight: 'Poids (kg)', field_height: 'Taille (cm)',
    summary_label: 'QUESTIONNAIRE',
  },
  de: {
    questions: [
      { id: 'q2', text: 'Möchten Sie für sich abnehmen oder einer nahestehenden Person helfen?', type: 'single', options: ['Für mich', 'Für eine nahestehende Person'] },
      { id: 'q3', text: 'Wie viele Kilo möchten Sie abnehmen?', type: 'single', options: ['Bis 5 kg', '5–10 kg', '10–20 kg', 'Mehr als 20 kg'] },
      { id: 'q4', text: 'Erzählen Sie etwas über sich:', type: 'data', fields: [
        { key: 'age', label: 'Alter' },
        { key: 'weight', label: 'Aktuelles Gewicht (kg)' },
        { key: 'height', label: 'Größe (cm)' },
      ] },
      { id: 'q5', text: 'Haben Sie früher erfolgreich abgenommen?', type: 'single', options: ['Ja, hat geklappt', 'Versucht, ohne Erfolg', 'Noch nie versucht'], keys: ['yes', 'tried', 'never'] },
      { id: 'q6', text: 'Falls ja — kam das Gewicht zurück?', type: 'single_custom', options: ['Ja, vollständig', 'Teilweise', 'Blieb stabil'], skipIf: SKIP_NEVER_TRIED },
      { id: 'q7', text: 'Wie verändert sich Ihr Gewicht aktuell?', type: 'single_custom', options: ['Steigt langsam', 'Bleibt gleich', 'Schwankt'] },
      { id: 'q8', text: 'Fällt es manchmal schwer aufzuhören zu essen?', type: 'single', options: ['Ja, oft', 'Manchmal', 'Selten', 'Nein'], keys: ['often', 'sometimes', 'rarely', 'no'] },
      { id: 'q9', text: 'Wann passiert das am häufigsten?', type: 'single_custom', options: ['Morgens', 'Mittags', 'Abends', 'Nachts'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q10', text: 'Was löst es meist aus?', type: 'multi_custom', options: ['Müdigkeit', 'Stress', 'Langeweile', 'Gewohnheit', 'Geselligkeit'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q11', text: 'Bewegungsniveau:', type: 'single', options: ['Fast keine Bewegung', 'Leicht (Spaziergänge)', 'Mäßig (3–4×/Woche)', 'Hoch (Sport regelmäßig)'] },
      { id: 'q12', text: 'Wie schlafen Sie?', type: 'single_custom', options: ['Weniger als 6 h', '6–7 h', '7–8 h'] },
      { id: 'q13', text: 'Gesundheitliche Einschränkungen? (mehrere)', type: 'multi_custom', options: ['Blutdruck', 'Diabetes', 'Schilddrüse', 'Gelenke', 'Herz', 'Keine'] },
      { id: 'q14', text: 'Wie wichtig ist die Lösung jetzt?', type: 'single', options: ['1–3: Schaue nur', '4–6: Möchte, nicht eilig', '7–8: Wichtig, bereit', '9–10: Höchste Priorität'] },
    ],
    intro: (name) => `Schön, Sie kennenzulernen, ${name}. Damit ich genau auf Ihre Situation eingehen kann, stelle ich ein paar kurze Fragen. 2–3 Minuten.`,
    outro: (name) => `Danke, ${name}. Das Bild ist klar. Erzählen Sie nun in eigenen Worten — was passiert gerade und was haben Sie bereits versucht?`,
    next: 'Weiter', done: 'Fertig', custom: 'Sonstiges...',
    field_age: 'Alter', field_weight: 'Gewicht (kg)', field_height: 'Größe (cm)',
    summary_label: 'FRAGEBOGEN',
  },
  zh: {
    questions: [
      { id: 'q2', text: '您是想为自己减重，还是帮助亲友？', type: 'single', options: ['为自己', '为亲友'] },
      { id: 'q3', text: '希望减多少公斤？', type: 'single', options: ['5 公斤以内', '5–10 公斤', '10–20 公斤', '20 公斤以上'] },
      { id: 'q4', text: '请告诉我一些基本信息：', type: 'data', fields: [
        { key: 'age', label: '年龄' },
        { key: 'weight', label: '当前体重 (公斤)' },
        { key: 'height', label: '身高 (厘米)' },
      ] },
      { id: 'q5', text: '以前成功减过重吗？', type: 'single', options: ['是，有效果', '尝试过，没有效果', '从未尝试'], keys: ['yes', 'tried', 'never'] },
      { id: 'q6', text: '如果是 — 体重又回来了吗？', type: 'single_custom', options: ['是，全部回来了', '部分回来', '维持得不错'], skipIf: SKIP_NEVER_TRIED },
      { id: 'q7', text: '现在体重怎么变化？', type: 'single_custom', options: ['缓慢上升', '保持不变', '上下波动'] },
      { id: 'q8', text: '有时候很难停下来不吃吗？', type: 'single', options: ['经常', '有时', '很少', '不会'], keys: ['often', 'sometimes', 'rarely', 'no'] },
      { id: 'q9', text: '通常什么时间发生？', type: 'single_custom', options: ['早晨', '下午', '晚上', '深夜'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q10', text: '通常什么会触发暴食？', type: 'multi_custom', options: ['疲劳', '压力', '无聊', '习惯', '聚餐/节日'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q11', text: '运动量水平：', type: 'single', options: ['几乎不动', '轻度（散步）', '中等（每周 3–4 次）', '高（规律运动）'] },
      { id: 'q12', text: '睡眠情况？', type: 'single_custom', options: ['不到 6 小时', '6–7 小时', '7–8 小时'] },
      { id: 'q13', text: '有健康限制吗？（可多选）', type: 'multi_custom', options: ['血压', '糖尿病', '甲状腺', '关节', '心脏', '没有限制'] },
      { id: 'q14', text: '现在解决这个问题有多重要？', type: 'single', options: ['1–3：只是看看', '4–6：想做但不急', '7–8：重要，愿意行动', '9–10：最优先'] },
    ],
    intro: (name) => `${name}，很高兴认识您。为了立刻针对您的情况开展工作，我会问几个简短问题，大约 2–3 分钟。`,
    outro: (name) => `谢谢，${name}。情况清楚了。现在请用您自己的话告诉我——目前发生了什么？以前尝试过什么？`,
    next: '下一步', done: '完成', custom: '其他...',
    field_age: '年龄', field_weight: '体重 (公斤)', field_height: '身高 (厘米)',
    summary_label: '问卷',
  },
  ar: {
    questions: [
      { id: 'q2', text: 'هل تريد إنقاص الوزن لنفسك أم لمساعدة شخص قريب؟', type: 'single', options: ['لنفسي', 'لشخص قريب'] },
      { id: 'q3', text: 'كم كيلوغرامًا تريد أن تخسر؟', type: 'single', options: ['حتى 5 كغ', '5–10 كغ', '10–20 كغ', 'أكثر من 20 كغ'] },
      { id: 'q4', text: 'أخبرني قليلاً عن نفسك:', type: 'data', fields: [
        { key: 'age', label: 'العمر' },
        { key: 'weight', label: 'الوزن الحالي (كغ)' },
        { key: 'height', label: 'الطول (سم)' },
      ] },
      { id: 'q5', text: 'هل سبق أن نجحت في إنقاص وزنك؟', type: 'single', options: ['نعم، نجح', 'حاولت دون نتيجة', 'لم أحاول أبدًا'], keys: ['yes', 'tried', 'never'] },
      { id: 'q6', text: 'إذا نعم — هل عاد الوزن؟', type: 'single_custom', options: ['نعم، عاد كله', 'عاد جزء منه', 'بقي ثابتًا'], skipIf: SKIP_NEVER_TRIED },
      { id: 'q7', text: 'كيف يتغير وزنك الآن؟', type: 'single_custom', options: ['يزداد ببطء', 'ثابت', 'يتأرجح'] },
      { id: 'q8', text: 'هل يصعب أحيانًا التوقف عن الأكل؟', type: 'single', options: ['نعم، كثيرًا', 'أحيانًا', 'نادرًا', 'لا'], keys: ['often', 'sometimes', 'rarely', 'no'] },
      { id: 'q9', text: 'متى يحدث هذا غالبًا؟', type: 'single_custom', options: ['صباحًا', 'ظهرًا', 'مساءً', 'ليلاً'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q10', text: 'ما الذي يحفّز الإفراط في الأكل عادةً؟', type: 'multi_custom', options: ['التعب', 'التوتر', 'الملل', 'العادة', 'الولائم/الاجتماعات'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q11', text: 'مستوى النشاط البدني:', type: 'single', options: ['قليل جدًا', 'خفيف (مشي)', 'متوسط (3–4 مرات أسبوعيًا)', 'عالٍ (رياضة منتظمة)'] },
      { id: 'q12', text: 'كيف نومك؟', type: 'single_custom', options: ['أقل من 6 ساعات', '6–7 ساعات', '7–8 ساعات'] },
      { id: 'q13', text: 'هل لديك قيود صحية؟ (يمكن اختيار عدة)', type: 'multi_custom', options: ['الضغط', 'السكري', 'الغدة الدرقية', 'المفاصل', 'القلب', 'لا قيود'] },
      { id: 'q14', text: 'ما مدى أهمية حل هذا الآن؟', type: 'single', options: ['1–3: أتفرج فقط', '4–6: أرغب، غير مستعجل', '7–8: مهم، مستعد', '9–10: أولوية قصوى'] },
    ],
    intro: (name) => `سعدت بلقائك، ${name}. لأعمل مباشرةً على وضعك، سأطرح عدة أسئلة قصيرة. ستستغرق 2–3 دقائق.`,
    outro: (name) => `شكرًا، ${name}. الصورة واضحة. الآن أخبرني بكلماتك — ما الذي يحدث وماذا جربت سابقًا؟`,
    next: 'التالي', done: 'تم', custom: 'إجابة أخرى...',
    field_age: 'العمر', field_weight: 'الوزن (كغ)', field_height: 'الطول (سم)',
    summary_label: 'استبيان',
  },
  hi: {
    questions: [
      { id: 'q2', text: 'क्या आप अपने लिए वज़न कम करना चाहते हैं या किसी अपने की मदद के लिए?', type: 'single', options: ['अपने लिए', 'किसी अपने के लिए'] },
      { id: 'q3', text: 'कितने किलो कम करना चाहते हैं?', type: 'single', options: ['5 किग्रा तक', '5–10 किग्रा', '10–20 किग्रा', '20 किग्रा से अधिक'] },
      { id: 'q4', text: 'अपने बारे में बताइए:', type: 'data', fields: [
        { key: 'age', label: 'उम्र' },
        { key: 'weight', label: 'वज़न (किग्रा)' },
        { key: 'height', label: 'लंबाई (सेमी)' },
      ] },
      { id: 'q5', text: 'क्या पहले वज़न कम करने में सफलता मिली?', type: 'single', options: ['हाँ, मिला', 'कोशिश की, नतीजा नहीं', 'कभी कोशिश नहीं की'], keys: ['yes', 'tried', 'never'] },
      { id: 'q6', text: 'अगर हाँ — क्या वज़न वापस आ गया?', type: 'single_custom', options: ['हाँ, पूरा वापस', 'कुछ हिस्सा वापस', 'स्थिर रहा'], skipIf: SKIP_NEVER_TRIED },
      { id: 'q7', text: 'अभी आपका वज़न कैसे बदल रहा है?', type: 'single_custom', options: ['धीरे-धीरे बढ़ रहा', 'स्थिर है', 'ऊपर-नीचे होता है'] },
      { id: 'q8', text: 'क्या कभी खाना रोकना मुश्किल लगता है?', type: 'single', options: ['हाँ, अक्सर', 'कभी-कभी', 'शायद ही', 'नहीं'], keys: ['often', 'sometimes', 'rarely', 'no'] },
      { id: 'q9', text: 'यह सबसे अधिक कब होता है?', type: 'single_custom', options: ['सुबह', 'दोपहर', 'शाम', 'रात'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q10', text: 'अधिक खाने की वजह क्या होती है?', type: 'multi_custom', options: ['थकान', 'तनाव', 'बोरियत', 'आदत', 'सामाजिक/त्योहार'], skipIf: SKIP_NO_OVEREATING },
      { id: 'q11', text: 'शारीरिक सक्रियता:', type: 'single', options: ['लगभग नहीं', 'हल्की (टहलना)', 'मध्यम (हफ्ते में 3–4 बार)', 'अधिक (नियमित खेल)'] },
      { id: 'q12', text: 'नींद कैसी है?', type: 'single_custom', options: ['6 घंटे से कम', '6–7 घंटे', '7–8 घंटे'] },
      { id: 'q13', text: 'क्या स्वास्थ्य संबंधी सीमाएँ हैं? (एक से अधिक)', type: 'multi_custom', options: ['रक्तचाप', 'मधुमेह', 'थायरॉइड', 'जोड़ें', 'हृदय', 'कोई नहीं'] },
      { id: 'q14', text: 'अभी इसे हल करना कितना ज़रूरी है?', type: 'single', options: ['1–3: बस देख रहा', '4–6: चाहता हूँ, जल्दी नहीं', '7–8: ज़रूरी, तैयार', '9–10: सर्वोच्च प्राथमिकता'] },
    ],
    intro: (name) => `आपसे मिलकर खुशी हुई, ${name}। आपकी स्थिति पर सटीक काम करने के लिए कुछ छोटे सवाल पूछूँगा। 2–3 मिनट लगेंगे।`,
    outro: (name) => `धन्यवाद, ${name}। तस्वीर साफ़ है। अब अपने शब्दों में बताइए — अभी क्या हो रहा है और पहले क्या आज़माया?`,
    next: 'आगे', done: 'पूरा', custom: 'अन्य...',
    field_age: 'उम्र', field_weight: 'वज़न (किग्रा)', field_height: 'लंबाई (सेमी)',
    summary_label: 'प्रश्नावली',
  },
};

export function getIntakeQuestions(lang) {
  return Q(lang).questions;
}

export function getIntakeIntro(lang, name) {
  return Q(lang).intro(name);
}

export function getIntakeOutro(lang, name) {
  return Q(lang).outro(name);
}

export function getIntakeButtons(lang) {
  const v = Q(lang);
  return {
    next: v.next, done: v.done, custom: v.custom,
    field_age: v.field_age, field_weight: v.field_weight, field_height: v.field_height,
  };
}

export function nextIntakeStep(answers, currentIdx, lang) {
  const list = getIntakeQuestions(lang);
  for (let i = currentIdx + 1; i < list.length; i++) {
    const q = list[i];
    if (q.skipIf && q.skipIf(answers)) continue;
    return i;
  }
  return -1;
}

// Build the final summary in the user's language so the LLM stays consistent.
export function buildIntakeSummary(name, answers, lang) {
  const v = Q(lang);
  const q = (id) => answers[id] || '—';
  const weight = parseFloat(answers.q4_weight);
  const height = parseFloat(answers.q4_height);
  let bmi = '';
  if (weight > 0 && height > 0) {
    const m = height / 100;
    bmi = (weight / (m * m)).toFixed(1);
  }
  const lines = [
    `[${v.summary_label}]`,
    `${v.field_age.split(' ')[0]}: ${name}`, // simple "name" label fallback
    `Q2: ${q('q2')}`,
    `Q3: ${q('q3')}`,
    `${v.field_age}: ${answers.q4_age || '—'}, ${v.field_weight}: ${answers.q4_weight || '—'}, ${v.field_height}: ${answers.q4_height || '—'}${bmi ? ` (BMI ${bmi})` : ''}`,
    `Q5: ${q('q5')}`,
    answers.q6 ? `Q6: ${q('q6')}` : null,
    `Q7: ${q('q7')}`,
    `Q8: ${q('q8')}`,
    answers.q9 ? `Q9: ${q('q9')}` : null,
    answers.q10 ? `Q10: ${q('q10')}` : null,
    `Q11: ${q('q11')}`,
    `Q12: ${q('q12')}`,
    `Q13: ${q('q13')}`,
    `Q14: ${q('q14')}`,
  ].filter(Boolean);
  return lines.join('\n');
}

// Backward-compat exports — default to English.
export const INTAKE_QUESTIONS = getIntakeQuestions('en');
export const INTAKE_INTRO = (name) => getIntakeIntro('en', name);
export const INTAKE_OUTRO = (name) => getIntakeOutro('en', name);
