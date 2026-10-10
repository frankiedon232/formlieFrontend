/**
 * Per-workspace reusable building blocks for the mock: saved fields and option lists.
 * Seeded workspaces start with a few neutral sample lists. Persisted across dev reloads.
 */
import type { OptionList, PageDesign, SavedField, SavedTheme } from '#shared/types/forms'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { loadPersisted, savePersisted } from '../core/persist'
import { SEEDED_TENANT_IDS, type MockTenant } from './tenants'

interface TenantLibrary {
  fields: SavedField[]
  lists: OptionList[]
  /** The sample list with levels was added once (F15 M2); deleting it keeps it gone. */
  placesSeeded?: boolean
  productsSeeded?: boolean
  /** Formalie's lists got their options' translations once (2026-10-10). */
  defaultsTranslated?: boolean
  /** Saved designs; `forms_count` is computed when listing. */
  themes?: (Omit<SavedTheme, 'forms_count' | 'source' | 'name_key'> & { source?: SavedTheme['source'] })[]
  /** Saved page designs (Resources → Landing pages); `forms_count` is computed when listing. */
  pages?: (Omit<PageDesign, 'forms_count' | 'source' | 'name_key'> & { source?: PageDesign['source'] })[]
  /** Workspace templates (F9): a snapshot of a form, its design included. */
  templates?: WorkspaceTemplate[]
}

export interface WorkspaceTemplate {
  id: string
  name: string
  description: string
  category: string
  icon: string
  schema: FormSchemaV1
  /** The form it was saved from (updates come from that form; owner, 2026-10-03). */
  source_form_id?: string
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

const stores = new Map<string, TenantLibrary>(
  Object.entries(loadPersisted<Record<string, TenantLibrary>>('library', {})),
)

/**
 * Formalie's default lists in every language (owner, 2026-10-10): each English option label with its
 * translations, given to the options of the lists Formalie provides (libraryStore).
 */
const DEFAULT_OPTION_TRANSLATIONS: Record<string, Record<string, string>> = {
  "Low": {"fr":"Faible","es":"Baja","pt":"Baixa","de":"Niedrig","it":"Bassa","nl":"Laag","pl":"Niski","ru":"Низкий","uk":"Низький","tr":"Düşük","ar":"منخفضة","hi":"कम","bn":"কম","zh-CN":"低","ja":"低","ko":"낮음","id":"Rendah","vi":"Thấp","sw":"Chini"},
  "Medium": {"fr":"Moyenne","es":"Media","pt":"Média","de":"Mittel","it":"Media","nl":"Gemiddeld","pl":"Średni","ru":"Средний","uk":"Середній","tr":"Orta","ar":"متوسطة","hi":"मध्यम","bn":"মাঝারি","zh-CN":"中","ja":"中","ko":"보통","id":"Sedang","vi":"Trung bình","sw":"Wastani"},
  "High": {"fr":"Élevée","es":"Alta","pt":"Alta","de":"Hoch","it":"Alta","nl":"Hoog","pl":"Wysoki","ru":"Высокий","uk":"Високий","tr":"Yüksek","ar":"عالية","hi":"उच्च","bn":"উচ্চ","zh-CN":"高","ja":"高","ko":"높음","id":"Tinggi","vi":"Cao","sw":"Juu"},
  "Critical": {"fr":"Critique","es":"Crítica","pt":"Crítica","de":"Kritisch","it":"Critica","nl":"Kritiek","pl":"Krytyczny","ru":"Критический","uk":"Критичний","tr":"Kritik","ar":"حرجة","hi":"गंभीर","bn":"জটিল","zh-CN":"紧急","ja":"緊急","ko":"긴급","id":"Kritis","vi":"Nghiêm trọng","sw":"Hatari"},
  "Finance": {"fr":"Finance","es":"Finanzas","pt":"Finanças","de":"Finanzen","it":"Finanza","nl":"Financiën","pl":"Finanse","ru":"Финансы","uk":"Фінанси","tr":"Finans","ar":"المالية","hi":"वित्त","bn":"অর্থ","zh-CN":"财务","ja":"経理","ko":"재무","id":"Keuangan","vi":"Tài chính","sw":"Fedha"},
  "Operations": {"fr":"Opérations","es":"Operaciones","pt":"Operações","de":"Betrieb","it":"Operazioni","nl":"Operaties","pl":"Operacje","ru":"Операции","uk":"Операції","tr":"Operasyon","ar":"العمليات","hi":"संचालन","bn":"পরিচালনা","zh-CN":"运营","ja":"運用","ko":"운영","id":"Operasional","vi":"Vận hành","sw":"Uendeshaji"},
  "People": {"fr":"Personnel","es":"Personas","pt":"Pessoas","de":"Personal","it":"Persone","nl":"Personeel","pl":"Kadry","ru":"Персонал","uk":"Персонал","tr":"İnsan Kaynakları","ar":"الموارد البشرية","hi":"मानव संसाधन","bn":"মানব সম্পদ","zh-CN":"人事","ja":"人事","ko":"인사","id":"SDM","vi":"Nhân sự","sw":"Watu"},
  "Sales": {"fr":"Ventes","es":"Ventas","pt":"Vendas","de":"Vertrieb","it":"Vendite","nl":"Verkoop","pl":"Sprzedaż","ru":"Продажи","uk":"Продажі","tr":"Satış","ar":"المبيعات","hi":"बिक्री","bn":"বিক্রয়","zh-CN":"销售","ja":"営業","ko":"영업","id":"Penjualan","vi":"Kinh doanh","sw":"Mauzo"},
  "Support": {"fr":"Support","es":"Soporte","pt":"Suporte","de":"Support","it":"Assistenza","nl":"Support","pl":"Wsparcie","ru":"Поддержка","uk":"Підтримка","tr":"Destek","ar":"الدعم","hi":"सहायता","bn":"সহায়তা","zh-CN":"支持","ja":"サポート","ko":"지원","id":"Dukungan","vi":"Hỗ trợ","sw":"Msaada"},
  "Technology": {"fr":"Technologie","es":"Tecnología","pt":"Tecnologia","de":"Technologie","it":"Tecnologia","nl":"Technologie","pl":"Technologia","ru":"Технологии","uk":"Технології","tr":"Teknoloji","ar":"التكنولوجيا","hi":"प्रौद्योगिकी","bn":"প্রযুক্তি","zh-CN":"技术","ja":"テクノロジー","ko":"기술","id":"Teknologi","vi":"Công nghệ","sw":"Teknolojia"},
  "Monday": {"fr":"Lundi","es":"Lunes","pt":"Segunda-feira","de":"Montag","it":"Lunedì","nl":"Maandag","pl":"Poniedziałek","ru":"Понедельник","uk":"Понеділок","tr":"Pazartesi","ar":"الاثنين","hi":"सोमवार","bn":"সোমবার","zh-CN":"星期一","ja":"月曜日","ko":"월요일","id":"Senin","vi":"Thứ Hai","sw":"Jumatatu"},
  "Tuesday": {"fr":"Mardi","es":"Martes","pt":"Terça-feira","de":"Dienstag","it":"Martedì","nl":"Dinsdag","pl":"Wtorek","ru":"Вторник","uk":"Вівторок","tr":"Salı","ar":"الثلاثاء","hi":"मंगलवार","bn":"মঙ্গলবার","zh-CN":"星期二","ja":"火曜日","ko":"화요일","id":"Selasa","vi":"Thứ Ba","sw":"Jumanne"},
  "Wednesday": {"fr":"Mercredi","es":"Miércoles","pt":"Quarta-feira","de":"Mittwoch","it":"Mercoledì","nl":"Woensdag","pl":"Środa","ru":"Среда","uk":"Середа","tr":"Çarşamba","ar":"الأربعاء","hi":"बुधवार","bn":"বুধবার","zh-CN":"星期三","ja":"水曜日","ko":"수요일","id":"Rabu","vi":"Thứ Tư","sw":"Jumatano"},
  "Thursday": {"fr":"Jeudi","es":"Jueves","pt":"Quinta-feira","de":"Donnerstag","it":"Giovedì","nl":"Donderdag","pl":"Czwartek","ru":"Четверг","uk":"Четвер","tr":"Perşembe","ar":"الخميس","hi":"गुरुवार","bn":"বৃহস্পতিবার","zh-CN":"星期四","ja":"木曜日","ko":"목요일","id":"Kamis","vi":"Thứ Năm","sw":"Alhamisi"},
  "Friday": {"fr":"Vendredi","es":"Viernes","pt":"Sexta-feira","de":"Freitag","it":"Venerdì","nl":"Vrijdag","pl":"Piątek","ru":"Пятница","uk":"Пʼятниця","tr":"Cuma","ar":"الجمعة","hi":"शुक्रवार","bn":"শুক্রবার","zh-CN":"星期五","ja":"金曜日","ko":"금요일","id":"Jumat","vi":"Thứ Sáu","sw":"Ijumaa"},
  "Saturday": {"fr":"Samedi","es":"Sábado","pt":"Sábado","de":"Samstag","it":"Sabato","nl":"Zaterdag","pl":"Sobota","ru":"Суббота","uk":"Субота","tr":"Cumartesi","ar":"السبت","hi":"शनिवार","bn":"শনিবার","zh-CN":"星期六","ja":"土曜日","ko":"토요일","id":"Sabtu","vi":"Thứ Bảy","sw":"Jumamosi"},
  "Sunday": {"fr":"Dimanche","es":"Domingo","pt":"Domingo","de":"Sonntag","it":"Domenica","nl":"Zondag","pl":"Niedziela","ru":"Воскресенье","uk":"Неділя","tr":"Pazar","ar":"الأحد","hi":"रविवार","bn":"রবিবার","zh-CN":"星期日","ja":"日曜日","ko":"일요일","id":"Minggu","vi":"Chủ nhật","sw":"Jumapili"},
  "Very unhappy": {"fr":"Très mécontent","es":"Muy insatisfecho","pt":"Muito insatisfeito","de":"Sehr unzufrieden","it":"Molto insoddisfatto","nl":"Zeer ontevreden","pl":"Bardzo niezadowolony","ru":"Очень недоволен","uk":"Дуже незадоволений","tr":"Çok memnuniyetsiz","ar":"غير راضٍ تمامًا","hi":"बहुत असंतुष्ट","bn":"খুবই অসন্তুষ্ট","zh-CN":"非常不满意","ja":"非常に不満","ko":"매우 불만족","id":"Sangat tidak puas","vi":"Rất không hài lòng","sw":"Hajaridhika kabisa"},
  "Unhappy": {"fr":"Mécontent","es":"Insatisfecho","pt":"Insatisfeito","de":"Unzufrieden","it":"Insoddisfatto","nl":"Ontevreden","pl":"Niezadowolony","ru":"Недоволен","uk":"Незадоволений","tr":"Memnuniyetsiz","ar":"غير راضٍ","hi":"असंतुष्ट","bn":"অসন্তুষ্ট","zh-CN":"不满意","ja":"不満","ko":"불만족","id":"Tidak puas","vi":"Không hài lòng","sw":"Hajaridhika"},
  "Neutral": {"fr":"Neutre","es":"Neutral","pt":"Neutro","de":"Neutral","it":"Neutro","nl":"Neutraal","pl":"Neutralny","ru":"Нейтрально","uk":"Нейтрально","tr":"Nötr","ar":"محايد","hi":"तटस्थ","bn":"নিরপেক্ষ","zh-CN":"一般","ja":"普通","ko":"보통","id":"Netral","vi":"Trung lập","sw":"Wastani"},
  "Happy": {"fr":"Content","es":"Satisfecho","pt":"Satisfeito","de":"Zufrieden","it":"Soddisfatto","nl":"Tevreden","pl":"Zadowolony","ru":"Доволен","uk":"Задоволений","tr":"Memnun","ar":"راضٍ","hi":"संतुष्ट","bn":"সন্তুষ্ট","zh-CN":"满意","ja":"満足","ko":"만족","id":"Puas","vi":"Hài lòng","sw":"Ameridhika"},
  "Very happy": {"fr":"Très content","es":"Muy satisfecho","pt":"Muito satisfeito","de":"Sehr zufrieden","it":"Molto soddisfatto","nl":"Zeer tevreden","pl":"Bardzo zadowolony","ru":"Очень доволен","uk":"Дуже задоволений","tr":"Çok memnun","ar":"راضٍ جدًا","hi":"बहुत संतुष्ट","bn":"খুবই সন্তুষ্ট","zh-CN":"非常满意","ja":"非常に満足","ko":"매우 만족","id":"Sangat puas","vi":"Rất hài lòng","sw":"Ameridhika sana"},
}

const SYSTEM = { id: 'system', name: 'Formalie' }
const at = '2026-09-01T09:00:00.000Z'
const list = (id: string, name: string, labels: string[]): OptionList => ({
  id,
  name,
  // Formalie's lists come with their options in every language (owner, 2026-10-10)
  options: labels.map(label => ({ value: label.toLowerCase().replace(/[^a-z0-9]+/g, '_'), label, ...(DEFAULT_OPTION_TRANSLATIONS[label] ? { translations: { ...DEFAULT_OPTION_TRANSLATIONS[label] } } : {}) })),
  created_by: SYSTEM,
  created_at: at,
  updated_at: at,
})
/** Country → Region → City, a few neutral places on several continents (sample list with levels). */
const PLACES: Record<string, Record<string, string[]>> = {
  Brazil: { 'São Paulo': ['São Paulo', 'Campinas', 'Santos'], 'Rio de Janeiro': ['Rio de Janeiro', 'Niterói'] },
  Canada: { Ontario: ['Toronto', 'Ottawa', 'Hamilton'], Quebec: ['Montréal', 'Québec City'] },
  Germany: { Bavaria: ['Munich', 'Nuremberg', 'Augsburg'], Hesse: ['Frankfurt', 'Wiesbaden'] },
  India: { Maharashtra: ['Mumbai', 'Pune', 'Nagpur'], Karnataka: ['Bengaluru', 'Mysuru'] },
  Japan: { Tokyo: ['Shinjuku', 'Shibuya'], Osaka: ['Osaka', 'Sakai'] },
  Kenya: { Nairobi: ['Nairobi', 'Westlands'], Mombasa: ['Mombasa', 'Nyali'] },
}
const slug = (text: string) => text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
function placesList(): OptionList {
  const options: OptionList['options'] = []
  for (const [country, regions] of Object.entries(PLACES)) {
    options.push({ value: slug(country), label: country })
    for (const [region, cities] of Object.entries(regions)) {
      options.push({ value: `${slug(country)}_${slug(region)}`, label: region, level: 1, parent: slug(country) })
      for (const city of cities) options.push({ value: `${slug(country)}_${slug(region)}_${slug(city)}`, label: city, level: 2, parent: `${slug(country)}_${slug(region)}` })
    }
  }
  return { id: 'lst_places', name: 'Places', description: 'Country, region and city', levels: [{ key: 'country', label: 'Country' }, { key: 'region', label: 'Region' }, { key: 'city', label: 'City' }], options, created_by: SYSTEM, created_at: at, updated_at: at }
}

/** Products with details (price, category), a sample list for formulas and logic on details (leftovers L1). */
function productsList(): OptionList {
  const items: [string, number, string][] = [
    ['Standing desk', 420, 'Furniture'], ['Office chair', 189.5, 'Furniture'], ['Monitor 27 inch', 239, 'Equipment'],
    ['Laptop stand', 45, 'Equipment'], ['Headset', 79, 'Equipment'], ['Desk lamp', 32.5, 'Furniture'],
  ]
  return {
    id: 'lst_products',
    name: 'Sample products',
    description: 'Products with a price and a category, to try details in formulas and logic',
    columns: [{ key: 'price', label: 'Price' }, { key: 'category', label: 'Category' }],
    options: items.map(([label, price, category]) => ({ value: slug(label), label, attrs: { price, category } })),
    created_by: SYSTEM,
    created_at: at,
    updated_at: at,
  }
}

const SAMPLE_LISTS = () => [
  list('lst_priority', 'Priority', ['Low', 'Medium', 'High', 'Critical']),
  list('lst_departments', 'Departments', ['Finance', 'Operations', 'People', 'Sales', 'Support', 'Technology']),
  list('lst_weekdays', 'Days of the week', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
  list('lst_satisfaction', 'Satisfaction', ['Very unhappy', 'Unhappy', 'Neutral', 'Happy', 'Very happy']),
  placesList(),
  productsList(),
]

export function libraryOf(tenant: MockTenant): TenantLibrary {
  let store = stores.get(tenant.id)
  if (!store) {
    store = { fields: [], lists: SEEDED_TENANT_IDS.has(tenant.id) ? SAMPLE_LISTS() : [] }
    stores.set(tenant.id, store)
  } else if (SEEDED_TENANT_IDS.has(tenant.id) && !store.lists.some(item => item.id === 'lst_places') && !store.placesSeeded) {
    store.lists.push(placesList())
    store.placesSeeded = true
    saveLibrary()
  }
  if (SEEDED_TENANT_IDS.has(tenant.id) && !store.productsSeeded) {
    if (!store.lists.some(item => item.id === 'lst_products')) store.lists.push(productsList())
    store.productsSeeded = true
    saveLibrary()
  }
  const sample = store.lists.find(item => item.id === 'lst_products' && item.name === 'Products')
  if (sample) {
    sample.name = 'Sample products'
    saveLibrary()
  }
  // Once: Formalie's lists made before 2026-10-10 get their options in every language
  if (!store.defaultsTranslated) {
    for (const list of store.lists)
      if (list.created_by?.id === 'system')
        for (const option of list.options) if (DEFAULT_OPTION_TRANSLATIONS[option.label]) option.translations = { ...DEFAULT_OPTION_TRANSLATIONS[option.label], ...option.translations }
    store.defaultsTranslated = true
    saveLibrary()
  }
  return store
}

export const saveLibrary = () => savePersisted('library', () => Object.fromEntries(stores))
