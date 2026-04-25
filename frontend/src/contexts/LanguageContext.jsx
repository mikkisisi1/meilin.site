import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { TRANSLATIONS_EXTRA } from './translations-extra';

const LanguageContext = createContext(null);

const LANGUAGES = [
  { code: 'ru', name: 'Русский', native: 'Русский', flag: '\u{1F1F7}\u{1F1FA}' },
  { code: 'en', name: 'English', native: 'English', flag: '\u{1F1FA}\u{1F1F8}' },
  { code: 'zh', name: 'Chinese', native: '\u4E2D\u6587', flag: '\u{1F1E8}\u{1F1F3}' },
  { code: 'es', name: 'Spanish', native: 'Espa\u00F1ol', flag: '\u{1F1EA}\u{1F1F8}' },
  { code: 'ar', name: 'Arabic', native: '\u0627\u0644\u0639\u0631\u0628\u064A\u0629', flag: '\u{1F1F8}\u{1F1E6}' },
  { code: 'fr', name: 'French', native: 'Fran\u00E7ais', flag: '\u{1F1EB}\u{1F1F7}' },
  { code: 'de', name: 'German', native: 'Deutsch', flag: '\u{1F1E9}\u{1F1EA}' },
  { code: 'hi', name: 'Hindi', native: '\u0939\u093F\u0928\u094D\u0926\u0940', flag: '\u{1F1EE}\u{1F1F3}' },
];

const translations = {
  ru: {
    welcome: 'Добро пожаловать в Miro.Care',
    subtitle: 'Ваш ИИ-психолог доступен 24/7',
    login: 'Войти',
    register: 'Регистрация',
    email: 'Email',
    password: 'Пароль',
    name: 'Имя',
    chooseProblems: 'Что вас беспокоит?',
    chooseVoice: 'Выберите голос ИИ-психолога',
    male: 'Мужской',
    female: 'Женский',
    startChat: 'Начать разговор',
    tariffs: 'Тарифы',
    tariffPrompt: 'Выберите тариф для продолжения',
    minutesLeft: 'Осталось',
    min: 'мин',
    hours: 'ч',
    specialists: 'Специалисты',
    radio: 'Miro Radio',
    profile: 'Мой профиль',
    about: 'О проекте',
    contacts: 'Контакты',
    links: 'Ссылки',
    bookPsychologist: 'Запись к психологу',
    language: 'Язык',
    theme: 'Тема',
    light: 'Светлая',
    dark: 'Тёмная',
    system: 'Системная',
    logout: 'Выйти',
    sendMessage: 'Напишите сообщение...',
    freeSession: 'Бесплатная консультация',
    paidSession: 'Платная сессия',
    camera: 'Камера',
    gallery: 'Галерея',
    testFree: 'Тест: 3 мин бесплатно',
    bookConsultation: 'Записаться на консультацию',
    playing: 'Играет...',
    paused: 'На паузе',
    musicDesc: 'Музыка для расслабления',
    paymentSuccess: 'Оплата прошла успешно!',
    paymentProcessing: 'Проверяем оплату...',
    back: 'Назад',
    later: 'Позже',
    noAccount: 'Нет аккаунта?',
    haveAccount: 'Уже есть аккаунт?',
    anxiety: 'Тревога и паника',
    depression: 'Депрессия',
    relationships: 'Отношения',
    ptsd: 'ПТСР',
    self_esteem: 'Самооценка',
    eating_disorder: 'РПП',
    weight: 'Лишний вес',
    grief: 'Утрата и горе',
    meaning: 'Поиск смысла',
    other: 'Другое',
    expert: 'Эксперт проекта',
    missionTitle: 'О Miro.Care',
    missionText: 'Miro.Care — гибридная платформа психологической помощи, объединяющая ИИ-психолога и живых специалистов.',
    ctaButton: 'Психолог',
    advance: 'Аванс',
  },
  en: {
    welcome: 'Welcome to Miro.Care',
    subtitle: 'Your AI psychologist available 24/7',
    login: 'Sign In',
    register: 'Sign Up',
    email: 'Email',
    password: 'Password',
    name: 'Name',
    chooseProblems: 'What concerns you?',
    chooseVoice: 'Choose AI psychologist voice',
    male: 'Male',
    female: 'Female',
    startChat: 'Start conversation',
    tariffs: 'Plans',
    tariffPrompt: 'Choose a plan to continue',
    minutesLeft: 'Remaining',
    min: 'min',
    hours: 'h',
    specialists: 'Specialists',
    radio: 'Miro Radio',
    profile: 'My Profile',
    about: 'About',
    contacts: 'Contacts',
    links: 'Links',
    bookPsychologist: 'Book a psychologist',
    language: 'Language',
    theme: 'Theme',
    light: 'Light',
    dark: 'Dark',
    system: 'System',
    logout: 'Log Out',
    sendMessage: 'Type a message...',
    freeSession: 'Free consultation',
    paidSession: 'Paid session',
    camera: 'Camera',
    gallery: 'Gallery',
    testFree: 'Test: 3 min free',
    bookConsultation: 'Book consultation',
    playing: 'Playing...',
    paused: 'Paused',
    musicDesc: 'Music for relaxation',
    paymentSuccess: 'Payment successful!',
    paymentProcessing: 'Checking payment...',
    back: 'Back',
    later: 'Later',
    noAccount: "Don't have an account?",
    haveAccount: 'Already have an account?',
    anxiety: 'Anxiety & Panic',
    depression: 'Depression',
    relationships: 'Relationships',
    ptsd: 'PTSD',
    self_esteem: 'Self-esteem',
    eating_disorder: 'Eating Disorder',
    weight: 'Weight Issues',
    grief: 'Grief & Loss',
    meaning: 'Search for Meaning',
    other: 'Other',
    expert: 'Project Expert',
    missionTitle: 'About Miro.Care',
    missionText: 'Miro.Care is a hybrid mental health platform combining AI psychologist and live specialists.',
    ctaButton: 'Psychologist',
    advance: 'Advance',
  },
  zh: { welcome: '欢迎来到 Miro.Care', subtitle: '您的AI心理咨询师 24/7在线', login: '登录', register: '注册', email: '邮箱', password: '密码', name: '姓名', chooseProblems: '什么困扰着您？', chooseVoice: '选择AI心理咨询师的声音', male: '男性', female: '女性', startChat: '开始对话', tariffs: '套餐', tariffPrompt: '选择套餐以继续', minutesLeft: '剩余', min: '分钟', hours: '小时', specialists: '专家', radio: 'Miro广播', profile: '我的资料', about: '关于', contacts: '联系方式', links: '链接', bookPsychologist: '预约心理咨询', language: '语言', theme: '主题', light: '浅色', dark: '深色', system: '跟随系统', logout: '退出', sendMessage: '输入消息...', freeSession: '免费咨询', paidSession: '付费咨询', testFree: '试用：3分钟免费', bookConsultation: '预约咨询', playing: '播放中...', paused: '已暂停', musicDesc: '放松音乐', paymentSuccess: '支付成功！', paymentProcessing: '正在确认支付...', back: '返回', noAccount: '没有账号？', haveAccount: '已有账号？', anxiety: '焦虑与恐慌', depression: '抑郁', relationships: '人际关系', ptsd: '创伤后应激', self_esteem: '自尊心', eating_disorder: '饮食障碍', weight: '体重问题', grief: '丧失与哀伤', meaning: '寻找人生意义', other: '其他', expert: '项目专家', missionTitle: '关于 Miro.Care', missionText: 'Miro.Care 是一个结合AI心理咨询师和真人专家的心理健康平台。', ctaButton: '心理咨询' },
  es: { welcome: 'Bienvenido a Miro.Care', subtitle: 'Tu psicólogo IA disponible 24/7', login: 'Iniciar sesión', register: 'Registrarse', email: 'Correo', password: 'Contraseña', name: 'Nombre', chooseProblems: '¿Qué te preocupa?', chooseVoice: 'Elige la voz del psicólogo IA', male: 'Masculina', female: 'Femenina', startChat: 'Iniciar conversación', tariffs: 'Planes', tariffPrompt: 'Elige un plan para continuar', minutesLeft: 'Restante', min: 'min', hours: 'h', specialists: 'Especialistas', radio: 'Miro Radio', profile: 'Mi Perfil', about: 'Acerca de', contacts: 'Contactos', links: 'Enlaces', bookPsychologist: 'Reservar psicólogo', language: 'Idioma', theme: 'Tema', light: 'Claro', dark: 'Oscuro', system: 'Sistema', logout: 'Cerrar sesión', sendMessage: 'Escribe un mensaje...', freeSession: 'Consulta gratuita', paidSession: 'Sesión de pago', testFree: 'Prueba: 3 min gratis', bookConsultation: 'Reservar consulta', playing: 'Reproduciendo...', paused: 'En pausa', musicDesc: 'Música para relajarse', paymentSuccess: '¡Pago exitoso!', paymentProcessing: 'Verificando pago...', back: 'Volver', noAccount: '¿No tienes cuenta?', haveAccount: '¿Ya tienes cuenta?', anxiety: 'Ansiedad y pánico', depression: 'Depresión', relationships: 'Relaciones', ptsd: 'TEPT', self_esteem: 'Autoestima', eating_disorder: 'TCA', weight: 'Peso', grief: 'Duelo', meaning: 'Sentido de vida', other: 'Otro', expert: 'Experto del proyecto', missionTitle: 'Sobre Miro.Care', missionText: 'Miro.Care es una plataforma híbrida de salud mental.', ctaButton: 'Psicólogo', advance: 'Anticipo' },
  ar: { welcome: 'مرحبًا بك في Miro.Care', subtitle: 'معالجك النفسي بالذكاء الاصطناعي متاح 24/7', login: 'تسجيل الدخول', register: 'إنشاء حساب', email: 'البريد الإلكتروني', password: 'كلمة المرور', name: 'الاسم', chooseProblems: 'ما الذي يقلقك؟', chooseVoice: 'اختر صوت المعالج', male: 'ذكر', female: 'أنثى', startChat: 'بدء المحادثة', tariffs: 'الباقات', tariffPrompt: 'اختر باقة للمتابعة', minutesLeft: 'المتبقي', min: 'دقيقة', hours: 'ساعة', specialists: 'المتخصصون', radio: 'راديو ميرو', profile: 'ملفي الشخصي', about: 'حول', contacts: 'اتصل بنا', links: 'روابط', bookPsychologist: 'حجز معالج', language: 'اللغة', theme: 'المظهر', light: 'فاتح', dark: 'داكن', system: 'النظام', logout: 'تسجيل الخروج', sendMessage: 'اكتب رسالة...', freeSession: 'استشارة مجانية', paidSession: 'جلسة مدفوعة', testFree: 'تجربة: 3 دقائق مجانًا', bookConsultation: 'حجز استشارة', playing: 'قيد التشغيل...', paused: 'متوقف مؤقتًا', musicDesc: 'موسيقى للاسترخاء', paymentSuccess: 'تم الدفع بنجاح!', paymentProcessing: 'جارٍ التحقق...', back: 'رجوع', noAccount: 'ليس لديك حساب؟', haveAccount: 'لديك حساب بالفعل؟', anxiety: 'القلق والذعر', depression: 'الاكتئاب', relationships: 'العلاقات', ptsd: 'اضطراب ما بعد الصدمة', self_esteem: 'تقدير الذات', eating_disorder: 'اضطرابات الأكل', weight: 'الوزن الزائد', grief: 'الفقدان والحزن', meaning: 'البحث عن المعنى', other: 'أخرى', expert: 'خبير المشروع', missionTitle: 'حول Miro.Care', missionText: 'Miro.Care منصة هجينة للصحة النفسية.', ctaButton: 'معالج نفسي', advance: 'عربون' },
  fr: { welcome: 'Bienvenue sur Miro.Care', subtitle: 'Votre psychologue IA disponible 24/7', login: 'Connexion', register: "S'inscrire", email: 'Email', password: 'Mot de passe', name: 'Nom', chooseProblems: 'Qu\'est-ce qui vous préoccupe ?', chooseVoice: 'Choisissez la voix du psychologue IA', male: 'Masculine', female: 'Féminine', startChat: 'Commencer la conversation', tariffs: 'Forfaits', tariffPrompt: 'Choisissez un forfait pour continuer', minutesLeft: 'Restant', min: 'min', hours: 'h', specialists: 'Spécialistes', radio: 'Miro Radio', profile: 'Mon Profil', about: 'À propos', contacts: 'Contacts', links: 'Liens', bookPsychologist: 'Réserver un psychologue', language: 'Langue', theme: 'Thème', light: 'Clair', dark: 'Sombre', system: 'Système', logout: 'Déconnexion', sendMessage: 'Écrivez un message...', freeSession: 'Consultation gratuite', paidSession: 'Session payante', testFree: 'Test : 3 min gratuites', bookConsultation: 'Réserver une consultation', playing: 'En cours...', paused: 'En pause', musicDesc: 'Musique relaxante', paymentSuccess: 'Paiement réussi !', paymentProcessing: 'Vérification du paiement...', back: 'Retour', noAccount: "Pas de compte ?", haveAccount: 'Déjà un compte ?', anxiety: 'Anxiété et panique', depression: 'Dépression', relationships: 'Relations', ptsd: 'TSPT', self_esteem: 'Estime de soi', eating_disorder: 'TCA', weight: 'Poids', grief: 'Deuil', meaning: 'Sens de la vie', other: 'Autre', expert: 'Expert du projet', missionTitle: 'À propos de Miro.Care', missionText: 'Miro.Care est une plateforme hybride de santé mentale.', ctaButton: 'Psychologue', advance: 'Acompte' },
  de: { welcome: 'Willkommen bei Miro.Care', subtitle: 'Ihr KI-Psychologe, rund um die Uhr verfügbar', login: 'Anmelden', register: 'Registrieren', email: 'E-Mail', password: 'Passwort', name: 'Name', chooseProblems: 'Was beschäftigt Sie?', chooseVoice: 'Wählen Sie die Stimme des KI-Psychologen', male: 'Männlich', female: 'Weiblich', startChat: 'Gespräch beginnen', tariffs: 'Tarife', tariffPrompt: 'Wählen Sie einen Tarif, um fortzufahren', minutesLeft: 'Verbleibend', min: 'Min', hours: 'Std', specialists: 'Spezialisten', radio: 'Miro Radio', profile: 'Mein Profil', about: 'Über uns', contacts: 'Kontakte', links: 'Links', bookPsychologist: 'Psychologen buchen', language: 'Sprache', theme: 'Design', light: 'Hell', dark: 'Dunkel', system: 'System', logout: 'Abmelden', sendMessage: 'Nachricht schreiben...', freeSession: 'Kostenlose Beratung', paidSession: 'Bezahlte Sitzung', testFree: 'Test: 3 Min. kostenlos', bookConsultation: 'Beratung buchen', playing: 'Läuft...', paused: 'Pausiert', musicDesc: 'Entspannungsmusik', paymentSuccess: 'Zahlung erfolgreich!', paymentProcessing: 'Zahlung wird überprüft...', back: 'Zurück', noAccount: 'Kein Konto?', haveAccount: 'Bereits ein Konto?', anxiety: 'Angst & Panik', depression: 'Depression', relationships: 'Beziehungen', ptsd: 'PTBS', self_esteem: 'Selbstwertgefühl', eating_disorder: 'Essstörung', weight: 'Gewicht', grief: 'Trauer', meaning: 'Sinnsuche', other: 'Anderes', expert: 'Projektexperte', missionTitle: 'Über Miro.Care', missionText: 'Miro.Care ist eine hybride Plattform für psychische Gesundheit.', ctaButton: 'Psychologe', advance: 'Anzahlung' },
  hi: { welcome: 'Miro.Care में आपका स्वागत है', subtitle: 'आपका AI मनोवैज्ञानिक 24/7 उपलब्ध', login: 'लॉगिन', register: 'साइन अप', email: 'ईमेल', password: 'पासवर्ड', name: 'नाम', chooseProblems: 'आपको क्या चिंता है?', chooseVoice: 'AI मनोवैज्ञानिक की आवाज़ चुनें', male: 'पुरुष', female: 'महिला', startChat: 'बातचीत शुरू करें', tariffs: 'प्लान', tariffPrompt: 'जारी रखने के लिए प्लान चुनें', minutesLeft: 'शेष', min: 'मिनट', hours: 'घंटे', specialists: 'विशेषज्ञ', radio: 'Miro रेडियो', profile: 'मेरी प्रोफ़ाइल', about: 'के बारे में', contacts: 'संपर्क', links: 'लिंक', bookPsychologist: 'मनोवैज्ञानिक बुक करें', language: 'भाषा', theme: 'थीम', light: 'लाइट', dark: 'डार्क', system: 'सिस्टम', logout: 'लॉगआउट', sendMessage: 'संदेश लिखें...', freeSession: 'निःशुल्क परामर्श', paidSession: 'भुगतान सत्र', testFree: 'परीक्षण: 3 मिनट मुफ़्त', bookConsultation: 'परामर्श बुक करें', playing: 'चल रहा है...', paused: 'रुका हुआ', musicDesc: 'आराम का संगीत', paymentSuccess: 'भुगतान सफल!', paymentProcessing: 'भुगतान जाँच रहे हैं...', back: 'वापस', noAccount: 'खाता नहीं है?', haveAccount: 'पहले से खाता है?', anxiety: 'चिंता और घबराहट', depression: 'अवसाद', relationships: 'रिश्ते', ptsd: 'PTSD', self_esteem: 'आत्म-सम्मान', eating_disorder: 'खान-पान विकार', weight: 'वज़न', grief: 'शोक', meaning: 'जीवन का अर्थ', other: 'अन्य', expert: 'प्रोजेक्ट विशेषज्ञ', missionTitle: 'Miro.Care के बारे में', missionText: 'Miro.Care एक हाइब्रिड मानसिक स्वास्थ्य प्लेटफ़ॉर्म है।', ctaButton: 'मनोवैज्ञानिक' },
};

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    // Default language is English (Slim You rebrand). Migration v3 forces 'en' for existing users on first load.
    const saved = localStorage.getItem('miro_language');
    const migrated = localStorage.getItem('miro_lang_v3');
    if (!migrated) {
      localStorage.setItem('miro_lang_v3', '1');
      localStorage.setItem('miro_language', 'en');
      return 'en';
    }
    return saved || 'en';
  });

  useEffect(() => {
    localStorage.setItem('miro_language', lang);
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  }, [lang]);

  const t = useCallback((key) => (
    TRANSLATIONS_EXTRA[lang]?.[key]
    || translations[lang]?.[key]
    || TRANSLATIONS_EXTRA['en']?.[key]
    || translations['en']?.[key]
    || key
  ), [lang]);

  const setLangStable = useCallback((l) => setLang(l), []);

  const value = useMemo(() => ({
    lang, setLang: setLangStable, t, languages: LANGUAGES
  }), [lang, setLangStable, t]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
