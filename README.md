# End-to-End Analýza penzijného systému SR (Sociálna poisťovňa)

## 📊 O projekte
Tento projekt predstavuje kompletné **end-to-end dátové a softvérové riešenie** zamerané na automatizovaný zber, robustnú transformáciu a pokročilú vizualizáciu otvorených dát Sociálnej poisťovne Slovenskej republiky o dôchodkových dávkach za obdobie rokov 2020 až 2026.

Celé riešenie je navrhnuté ako trojstupňová produkčná pipeline:
1. **Resilient Data Downloader (Python):** Automatizovaný zber dát zo serverov Sociálnej poisťovne, ktorý úspešne prekonáva nekonzistentné ukladanie súborov na strane štátnej inštitúcie.
2. **Robustná ETL Pipeline (Python + Pandas):** Kompletné čistenie, unifikácia a transformácia neštruktúrovaných dát do relačnej štruktúry Star Schema.
3. **Korporátny Dashboard (Power BI):** Interaktívny report postavený na explicitnom DAX engine, implementujúci pokročilý UI/UX dizajn a data storytelling.

---

## 💡 Hlavné analytické zistenia (The Data Story)
* **Štrukturálny šok (2023/2024):** Dashboard jasne odhaľuje masívny anomálny nárast novopriznaných predčasných starobných dôchodkov koncom roka 2023 a začiatkom roka 2024, kedy ich podiel na novopriznaných dôchodkoch vyskočil z priemerných 15 % na viac ako 70 %.
* **Izolácia fenoménu (Doménová analýza):** Vďaka rozdeleniu reportu na špecifické hárky projekt exaktne dokazuje, že zatiaľ čo starobné dôchodky prešli legislatívnym výkyvom, štruktúra invalidných dôchodkov zostala v rovnakom období stabilná. To potvrdzuje, že išlo o politicko-legislatívny fenomén, nie celospoločenskú zmenu zdravotného stavu populácie.

---

## 🛠️ Použité technológie a Nástroje
* **Sťahovanie dát & Scraping:** Python (knižnice `requests`, `urllib.parse`)
* **ETL & Data Engineering:** Python (knižnice `pandas`, `openpyxl`, `re`, `unicodedata`, `glob`)
* **Dátové modelovanie & BI:** Power BI Desktop (VertiPaq engine, Star Schema, DAX)
* **Verziovanie:** Git & GitHub

---

## 📁 Štruktúra projektu a dátová hygiena
Projekt striktne dodržiava profesionálnu organizáciu priečinkov a separáciu zodpovednosti:

```text
sk-pension-analysis/
│
├── data/
│   ├── raw/          # Stiahnuté neštruktúrované Excel súbory (.xlsx)
│   └── processed/    # Vyčistené a exportované CSV tabuľky
│
├── logs/             # Automatické logy o priebehu sťahovania a ETL
│
├── scripts/
│   ├── download_data.py  # FÁZA 1: Stiahnutie dát z webu Sociálna poistovňa
│   └── transform_data.py # FÁZA 2: Robustná transformačná ETL pipeline (Star Schema)
│
├── sp_pension_report.pbix # FÁZA 3: Interaktívny Power BI report a dátový model
└── README.md         # Dokumentácia projektu
```

**⚙️ Detailná architektúra riešenia**

*📌 Fáza 1:* Resilientný zber dát (download_data.py)
Zdrojové datasety sú Sociálnou poisťovňou ukladané s vysokou mierou nekonzistentnosti. Skript tento problém rieši pomocou pokročilej logiky odolnosti:
* **Dynamické vyhľadávanie endpointov:** Generuje prioritný zoznam alternatívnych vzdialených ciest (YYYY-MM), keďže ľudský faktor v SP ukladá ročné uzávierky zakaždým do iných priečinkov.
* **Ochrana pred ľudskými chybami:** Obsahuje mechanizmus premostenia chýb v názvoch súborov (napr. úspešne zachytáva a spracováva kritický preklep z roku 2020: ...dôchodkového pistenia rok 2020.xlsx).
* **Efektívny sieťový traffic:** Využíva rýchle overovanie prítomnosti súboru pomocou HTTP HEAD požiadaviek a až po validácii (Status 200) spúšťa bezpečné streamovanie binárneho payloadu (requests.get).

*📌 Fáza 2:* ETL a Relačné modelovanie (transform_data.py)
Surové dáta z Excelov prechádzajú hĺbkovým čistením a pretavením do čistej hviezdicovej architektúry (Star Schema):
* **Textový parsing & Unifikácia:** Odstraňuje diakritiku, normalizuje formáty textov, zjednocuje slovenské názvy mesiacov na číselné indexy a extrahuje časový kontext priamo z metadát súborov.
* **Ochrana pred kolíziou kľúčových slov:** Vyhľadávací mapovací algoritmus typov dôchodkov (PENSION_MAP) automaticky radí kľúče podľa dĺžky (od najdlhšieho po najkratší). Tým sa garantuje, že reťazec "starobný" nepredbehne a nepohltí špecifický "predčasný starobný dôchodok".
* **Export do Dátového skladu:** Skript generuje tri optimalizované CSV súbory, pričom dimenzie (dim_date, dim_pension_type) už obsahujú indexy zoradenia vygenerované priamo z Pythonu (Pension_Sort_Order, Year_Month).

*📌 Fáza 3:* Power BI Analytický model & UI/UX
Dáta sú prepojené v čistej hviezdicovej mriežke (1:N vzťahy medzi Dimenziami a Faktovou tabuľkou fact_pensions).
* **DAX Engine:** Výpočty KPI kariet sú postavené na exaktnej funkcii AVERAGE, ktorá dynamicky reaguje na filter časovej osi (napr. pri roku 2026 automaticky zosumarizuje dostupné mesiace a vypočíta správny aritmetický priemer).
* **Domain Color-Coding (Farebné kódovanie):** Report využíva psychológiu farieb na okamžitú orientáciu užívateľa na jednotlivých hárkoch:
* **Čisté UI bez scrollbarov:** Os X je nastavená na plynulý režim Continuous vďaka dátovému formátu zladenému na úrovni modelu, čo odstránilo vizuálne rušivé posuvníky.
<img width="1119" height="628" alt="image" src="https://github.com/user-attachments/assets/98e6db35-fbec-42e5-a5d3-548056c4fe9a" />

**🚀 Ako spustiť projekt lokálne (Krok za krokom)**

* *Klonovanie repozitára:* git clone [https://github.com/DomiBal/sk-pension-analysis.git](https://github.com/DomiBal/sk-pension-analysis.git)
cd sk-pension-analysis
* *Inštalácia závislostí:* Uisti sa, že máš nainštalované potrebné Python knižnice pre prácu so sieťou a Excelmi - pip install requests pandas openpyxl
* *Spustenie Fázy 1 (Stiahnutie zdrojových dát):* 
Skript autonómne stiahne ročné datasety priamo zo serverov Sociálnej poisťovne: python scripts/download_data.py
* *Spustenie Fázy 2 (Transformácia a ETL):*
Skript spracuje surové Excel súbory, vykoná čistenie a do data/processed/ uloží hotové CSV súbory: python scripts/transform_data.py
* *Otvorenie a Refresh reportu:* Spusť report sp_pension_report.pbix v aplikácii Power BI Desktop a na hlavnej karte klikni na Refresh. Model automaticky nasaje čerstvo vygenerované dáta z Pythonu.

Autor: Dominika Balabanova
