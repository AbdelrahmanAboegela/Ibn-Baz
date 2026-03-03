# Ibn Baz Scraper

This repository contains a high-performance web scraper designed to extract a structured dataset from the official [BinBaz.org.sa](https://binbaz.org.sa/) website. 

The project was built as part of an NLP course to gather clean Arabic text data for downstream natural language processing tasks, such as Retrieval-Augmented Generation (RAG) and Graph-based knowledge extraction.

## Dataset Overview

The scraper extracts `.jsonl` data across multiple content types:

| Content Type | Estimated Count | Description |
|:---|:---:|:---|
| **Fatwas** | ~24,600 | Structured Q&A with deep nested extraction for follow-up questions. |
| **Audios** | ~3,400 | Extracts audio page URLs and full on-page text transcripts, splitting lectures from Q&A sessions. |
| **Speeches** | ~300 | Written transcripts of speeches. |
| **Articles** | ~170 | Written articles and essays. |
| **Pearls** | ~120 | Short wisdom notes ("درر"). |
| **Discussions** | ~130 | Transcripts of discussions and debates. |
| **Books** | ~250 | Books metadata, filtering out non-Arabic translated books. |

### Data Format (JSONL)

All output is saved in the `output/` directory as `[type].jsonl`. Due to the complexity of the data, the scraper aggressively parses structures like inline Q&As and related URLs. 

Here is an example structure of a scraped **Fatwa** record:

```json
{
  "content_type": "fatwa",
  "fatwa_id": 8,
  "url": "https://binbaz.org.sa/fatwas/8/حكم-التميمة-من-القران",
  "title": "حكم التميمة من القرآن",
  "question": "ما حكم التميمة من القرآن ومن غيره؟",
  "answer_direct": "أما التميمة من غير القرآن كالعظام والطلاسم والودع وشعر الذئب وما أشبه ذلك فهذه منكرة محرمة بالنص، لا يجوز تعليقها على الطفل ولا على غير الطفل؛ لقوله ﷺ: من تعلق تميمة فلا أتم الله له، ومن تعلق ودعة فلا ودع الله له ، وفي رواية: من تعلق تميمة فقد أشرك . أما إذا كانت من القرآن أو من دعوات معروفة طيبة، فهذه اختلف فيها العلماء، فقال بعضهم: يجوز تعليقها، ويروى هذا عن جماعة من السلف جعلوها كالقراءة على المريض. والقول الثاني: أنها لا تجوز وهذا هو المعروف عن عبدالله بن مسعود وحذيفة رضي الله عنهما وجماعة من السلف والخلف قالوا: لا يجوز تعليقها ولو كانت من القرآن سدًا للذريعة وحسمًا لمادة الشرك وعملًا بالعموم؛ لأن الأحاديث المانعة من التمائم أحاديث عامة، لم تستثن شيئًا. والواجب: الأخذ بالعموم فلا يجوز شيء من التمائم أصلًا؛ لأن ذلك يفضي إلى تعليق غيرها والتباس الأمر. فوجب منع الجميع، وهذا هو الصواب لظهور دليله. فلو أجزنا التميمة من القرآن ومن الدعوات الطيبة لانفتح الباب وصار كل واحد يعلق ما شاء، فإذا أنكر عليه، قال: هذا من القرآن، أو هذه من الدعوات الطيبة، فينفتح الباب، ويتسع الخرق وتلبس التمائم كلها. وهناك علة ثالثة وهي: أنها قد يدخل بها الخلاء ومواضع القذر، ومعلوم أن كلام الله ينزه عن ذلك، ولا يليق أن يدخل به الخلاء",
  "nested_qa": [],
  "answer": "أما التميمة من غير القرآن كالعظام والطلاسم والودع وشعر الذئب وما أشبه ذلك فهذه منكرة محرمة بالنص، لا يجوز تعليقها على الطفل ولا على غير الطفل؛ لقوله ﷺ: من تعلق تميمة فلا أتم الله له، ومن تعلق ودعة فلا ودع الله له ، وفي رواية: من تعلق تميمة فقد أشرك . أما إذا كانت من القرآن أو من دعوات معروفة طيبة، فهذه اختلف فيها العلماء، فقال بعضهم: يجوز تعليقها، ويروى هذا عن جماعة من السلف جعلوها كالقراءة على المريض. والقول الثاني: أنها لا تجوز وهذا هو المعروف عن عبدالله بن مسعود وحذيفة رضي الله عنهما وجماعة من السلف والخلف قالوا: لا يجوز تعليقها ولو كانت من القرآن سدًا للذريعة وحسمًا لمادة الشرك وعملًا بالعموم؛ لأن الأحاديث المانعة من التمائم أحاديث عامة، لم تستثن شيئًا. والواجب: الأخذ بالعموم فلا يجوز شيء من التمائم أصلًا؛ لأن ذلك يفضي إلى تعليق غيرها والتباس الأمر. فوجب منع الجميع، وهذا هو الصواب لظهور دليله. فلو أجزنا التميمة من القرآن ومن الدعوات الطيبة لانفتح الباب وصار كل واحد يعلق ما شاء، فإذا أنكر عليه، قال: هذا من القرآن، أو هذه من الدعوات الطيبة، فينفتح الباب، ويتسع الخرق وتلبس التمائم كلها. وهناك علة ثالثة وهي: أنها قد يدخل بها الخلاء ومواضع القذر، ومعلوم أن كلام الله ينزه عن ذلك، ولا يليق أن يدخل به الخلاء",
  "source_ref": "مجموع فتاوى العلامة ابن باز (1/ 51)",
  "text": "ما حكم التميمة من القرآن ومن غيره؟ أما التميمة من غير القرآن...",
  "categories": [
    "الرقى والتمائم"
  ],
  "related": [
    {
      "url": "https://binbaz.org.sa/fatwas/45/حكم-تعليق-التعاويذ-التي-تحتوي-على-ايات-قرانية",
      "title": "حكم تعليق التعاويذ التي تحتوي على آيات قرآنية"
    },
    {
      "url": "https://binbaz.org.sa/fatwas/899/حكم-الحجب-والتوسل-ببركة-الصالحين-والصلاة-خلف-من-يفعله",
      "title": "حكم الحُجُب والتوسل ببركة الصالحين والصلاة خلف من يفعله"
    },
    {
      "url": "https://binbaz.org.sa/fatwas/9/الرقى-والتمايم-والتولة-شرك",
      "title": "الرقى والتمائم والتولة شرك"
    }
  ],
  "related_ids": [
    45,
    899,
    9
  ],
  "audio_url": "",
  "scraped_at": "2026-03-03T01:01:41.101451"
}
```

*Note on Extraction Logic:*  
- The `question` field automatically identifies the question block (often deeply nested in HTML) and strips prefixes like "السؤال" or "س:".
- The `answer` parses the fatwa's response, extracting footnotes to a `source_ref` string.
- The scraper intelligently searches for nested Q&A pairs within the answer body structure, saving following questions into `nested_qa`.
- Explicit relationships to other entities are pulled into `related_ids` array, making it instantly adaptable for Graph-RAG structures.

## Technical Details

The scraper is written in Python and leverages [Scrapling](https://scrapling.readthedocs.io/).

- **Robust Concurrency:** Uses multi-threaded extraction logic.
- **Resumability:** The scraper state reads existing JSONL files on boot. Passing `--crawldir crawl_state` enables Scrapling-level pause/resume logic so no request is duplicated.
- **Sitemap Navigation:** Automatically discovers all content by parsing the root `sitemap-index.xml`.

## Setup & Installation

### Requirements
- Python 3.10+
- Install dependencies: `pip install -r requirements.txt`

### Usage

**1. Run the Full Pipeline:**
This command will discover URLs via the sitemap and pull everything.
```bash
python run.py
```

**2. Scrape Specific Types:**
Limit the scraper to specific content types via `--types`
```bash
python run.py --types fatwa audio
```

**3. Test Run:**
Run with a limit strictly for verification
```bash
python run.py --limit 50
```
