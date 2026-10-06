/**
 * The icon a label asks for (owner, 2026-10-06: "First name" → a person, "Company" → a building,
 * not the same text icon on every short answer). A built-in list of words in the common languages,
 * checked on the label and the key; the first rule that matches wins, so specific words come first.
 * Nothing matches → the field type's own icon. Built-in first, no outside service.
 */

const RULES: [icon: string, words: string[]][] = [
  ['i-lucide-cake', ['date of birth', 'birth date', 'birthday', 'dob', 'born', 'fecha de nacimiento', 'date de naissance', 'geburtsdatum', 'data di nascita', 'data de nascimento', 'geboortedatum', 'tanggal lahir', 'doğum tarihi', 'дата рождения']],
  ['i-lucide-lock', ['password', 'passcode', 'pin code', 'contraseña', 'mot de passe', 'passwort', 'senha', 'wachtwoord', 'пароль']],
  ['i-lucide-at-sign', ['username', 'user name', 'handle', 'nickname', "nom d'utilisateur", 'benutzername', 'nombre de usuario']],
  ['i-lucide-mail', ['email', 'e-mail', 'e mail', 'correo', 'courriel', 'posta elettronica', 'почта']],
  ['i-lucide-phone', ['phone', 'mobile', 'telephone', 'tel', 'cell', 'whatsapp', 'teléfono', 'telefono', 'téléphone', 'telefon', 'telefone', 'celular', 'handy', 'телефон', 'nomor hp']],
  ['i-lucide-briefcase', ['job title', 'position', 'role', 'occupation', 'profession', 'job', 'puesto', 'cargo', 'poste', 'fonction', 'beruf', 'stelle', 'functie', 'pekerjaan', 'должность', 'experience', 'years of experience']],
  ['i-lucide-building-2', ['company', 'organisation', 'organization', 'business', 'employer', 'firm', 'agency', 'institution', 'empresa', 'entreprise', 'société', 'firma', 'unternehmen', 'azienda', 'bedrijf', 'perusahaan', 'şirket', 'компания']],
  ['i-lucide-users', ['department', 'team', 'guests', 'attendees', 'participants', 'people', 'employees', 'company size', 'number of people', 'household', 'departamento', 'abteilung', 'reparto', 'afdeling']],
  ['i-lucide-user', ['first name', 'last name', 'surname', 'family name', 'given name', 'full name', 'middle name', 'your name', 'apellido', 'prénom', 'vorname', 'nachname', 'cognome', 'sobrenome', 'voornaam', 'achternaam', 'soyad', 'фамилия', 'contact person', 'nombre completo', 'nom complet']],
  ['i-lucide-flag', ['nationality', 'citizenship', 'nacionalidad', 'nationalité', 'staatsangehörigkeit', 'nazionalità', 'nacionalidade']],
  ['i-lucide-mailbox', ['zip', 'zipcode', 'zip code', 'postal', 'postcode', 'post code', 'código postal', 'code postal', 'postleitzahl', 'cap', 'cep', 'postcode']],
  ['i-lucide-building', ['city', 'town', 'village', 'ciudad', 'ville', 'stadt', 'ort', 'città', 'cidade', 'plaats', 'kota', 'şehir', 'город']],
  ['i-lucide-map', ['state', 'region', 'province', 'county', 'district', 'provincia', 'estado', 'région', 'bundesland', 'regione', 'provinsi']],
  ['i-lucide-earth', ['country', 'país', 'pays', 'land', 'paese', 'negara', 'ülke', 'страна']],
  ['i-lucide-map-pin', ['address', 'street', 'location', 'venue', 'dirección', 'domicilio', 'adresse', 'straße', 'strasse', 'indirizzo', 'endereço', 'adres', 'alamat', 'адрес']],
  ['i-lucide-globe', ['website', 'web site', 'url', 'site', 'homepage', 'portfolio', 'sitio web', 'site web', 'webseite', 'sito']],
  ['i-lucide-link', ['linkedin', 'profile link', 'link', 'social']],
  ['i-lucide-id-card', ['passport', 'national id', 'id number', 'identity', 'licence', 'license', 'ssn', 'tax id', 'pasaporte', 'passeport', 'reisepass', 'documento', 'dni', 'nif', 'cpf']],
  ['i-lucide-landmark', ['bank', 'iban', 'account number', 'swift', 'routing', 'banco', 'banque']],
  ['i-lucide-receipt', ['invoice', 'order number', 'reference', 'receipt', 'vat', 'tax', 'factura', 'facture', 'rechnung', 'fattura', 'fatura', 'referencia', 'référence']],
  ['i-lucide-banknote', ['price', 'amount', 'cost', 'budget', 'salary', 'fee', 'total', 'payment', 'income', 'revenue', 'rate', 'precio', 'importe', 'presupuesto', 'salario', 'prix', 'montant', 'salaire', 'preis', 'betrag', 'gehalt', 'prezzo', 'importo', 'preço', 'valor', 'prijs', 'bedrag', 'harga', 'gaji', 'fiyat', 'цена']],
  ['i-lucide-hash', ['quantity', 'qty', 'how many', 'number of', 'count', 'cantidad', 'quantité', 'anzahl', 'menge', 'quantità', 'quantidade', 'aantal', 'jumlah', 'adet', 'количество']],
  ['i-lucide-hourglass', ['age', 'edad', 'âge', 'alter', 'età', 'idade', 'leeftijd', 'usia', 'yaş', 'возраст']],
  ['i-lucide-venus-and-mars', ['gender', 'sex', 'género', 'genre', 'geschlecht', 'genere', 'gênero', 'geslacht', 'jenis kelamin', 'cinsiyet', 'пол']],
  ['i-lucide-graduation-cap', ['school', 'university', 'college', 'education', 'degree', 'qualification', 'course', 'escuela', 'universidad', 'école', 'université', 'schule', 'universität', 'scuola', 'escola', 'universidade']],
  ['i-lucide-package', ['product', 'item', 'model', 'producto', 'produit', 'produkt', 'prodotto', 'produto', 'barang']],
  ['i-lucide-truck', ['delivery', 'shipping', 'courier', 'entrega', 'envío', 'livraison', 'lieferung', 'consegna']],
  ['i-lucide-calendar-check', ['appointment', 'booking', 'reservation', 'event', 'arrival', 'check-in', 'check in', 'cita', 'reserva', 'rendez-vous', 'termin', 'appuntamento']],
  ['i-lucide-car', ['vehicle', 'car', 'licence plate', 'license plate', 'registration number', 'vehículo', 'véhicule', 'fahrzeug', 'veicolo', 'veículo']],
  ['i-lucide-heart-pulse', ['medical', 'health', 'allergy', 'allergies', 'medication', 'condition', 'diet', 'dietary', 'médico', 'salud', 'santé', 'gesundheit', 'salute', 'saúde']],
  ['i-lucide-siren', ['emergency', 'emergencia', 'urgence', 'notfall', 'emergenza']],
  ['i-lucide-languages', ['language', 'idioma', 'langue', 'sprache', 'lingua', 'taal', 'bahasa', 'dil', 'язык']],
  ['i-lucide-accessibility', ['accessibility', 'accessible', 'disability', 'special needs', 'accesibilidad', 'accessibilité', 'barrierefreiheit', 'accessibilità', 'acessibilidade']],
  ['i-lucide-megaphone', ['source', 'campaign', 'how did you hear', 'heard about', 'referral', 'referred by', 'origin', 'origen', 'origine', 'fuente', 'campaña', 'campagne', 'kampagne', 'quelle', 'fonte', 'campanha', 'bron', 'sumber', 'kaynak']],
  ['i-lucide-signal-high', ['priority', 'urgency', 'severity', 'importance', 'prioridad', 'priorité', 'priorität', 'priorità', 'prioridade', 'prioriteit', 'prioritas', 'öncelik']],
  ['i-lucide-heart-handshake', ['relationship', 'relation', 'next of kin', 'parentesco', 'relación', 'lien', 'beziehung', 'relazione', 'relação']],
  ['i-lucide-award', ['loyalty', 'membership', 'member level', 'tier', 'fidelidad', 'fidélité', 'treue', 'fedeltà', 'fidelidade']],
  ['i-lucide-sparkles', ['interested', 'interests', 'interest', 'hobby', 'hobbies', 'pastime', 'intereses', 'intérêts', 'interessen', 'interessi', 'interesses', 'hobi']],
  ['i-lucide-list-checks', ['actions taken', 'steps taken', 'action taken', 'next steps', 'measures']],
  ['i-lucide-calendar-range', ['period', 'range', 'days of the week', 'weekdays', 'availability', 'duration', 'periodo', 'période', 'zeitraum', 'período', 'periode']],
  ['i-lucide-banknote', ['subtotal', 'estimate', 'quote', 'deposit', 'discount', 'estimación', 'devis', 'schätzung', 'preventivo', 'orçamento']],
  ['i-lucide-user-round-check', ['reported by', 'submitted by', 'requested by', 'approved by', 'assigned to', 'owner', 'manager', 'supervisor', 'witness']],
  ['i-lucide-users', ['departments', 'groups', 'group']],
  ['i-lucide-message-square', ['describe', 'what happened', 'what could', 'what would', 'what are', 'what is', 'what was', 'instead', 'improve', 'better', 'suggestion', 'suggestions', 'disappointed', 'win back', 'keep you', 'reason', 'reasons', 'how can we', 'how could we', 'qué', 'pourquoi', 'warum']],
  ['i-lucide-map-pin', ['where', 'dónde', 'où', 'wo', 'dove', 'onde', 'waar', 'di mana', 'nerede']],
  ['i-lucide-calendar', ['when', 'cuándo', 'quand', 'wann', 'quando', 'wanneer', 'kapan', 'ne zaman']],
  ['i-lucide-tag', ['subject', 'topic', 'title', 'category', 'type', 'asunto', 'tema', 'sujet', 'objet', 'betreff', 'thema', 'oggetto', 'assunto', 'onderwerp', 'subjek', 'konu', 'тема']],
  ['i-lucide-message-square', ['comment', 'comments', 'message', 'notes', 'note', 'feedback', 'description', 'details', 'tell us', 'why', 'explain', 'question', 'remarks', 'anything else', 'comentario', 'mensaje', 'descripción', 'commentaire', 'message', 'kommentar', 'nachricht', 'beschreibung', 'commento', 'messaggio', 'comentário', 'mensagem', 'opmerking', 'pesan', 'komentar', 'yorum', 'mesaj', 'комментарий', 'сообщение']],
  ['i-lucide-search', ['search', 'keyword', 'keywords', 'buscar', 'recherche', 'suche', 'cerca']],
  ['i-lucide-clock', ['time', 'hora', 'heure', 'uhrzeit', 'orario', 'horário', 'tijd', 'waktu', 'saat', 'время']],
  ['i-lucide-calendar', ['date', 'day', 'fecha', 'jour', 'datum', 'tanggal', 'tarih', 'дата']],
  // Last: a plain "name" ("Product name" and "Company name" matched above)
  ['i-lucide-user', ['name', 'nombre', 'nom', 'nome', 'naam', 'nama', 'isim', 'имя']],
]

const normalise = (text: string) =>
  ` ${text
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[_\-./:()?!,;*]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()} `
/** The rules, with their words normalised once (accents off), matched as whole words. */
const PREPARED = RULES.map(([icon, words]) => [icon, words.map(word => normalise(word))] as const)

/** The icon a label (or key) points to, or null when no word matches. */
export function iconFromLabel(label: string | null | undefined, key?: string | null): string | null {
  for (const text of [label, key]) {
    if (!text?.trim()) continue
    const haystack = normalise(text)
    for (const [icon, words] of PREPARED) if (words.some(word => haystack.includes(word))) return icon
  }
  return null
}
