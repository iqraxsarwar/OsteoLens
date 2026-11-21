"""Turkish interface responses; quoted publication text remains unmodified."""
import json
import requests


def english_search_query(question):
    from backend.rag_assistant import OLLAMA_BASE_URL, OLLAMA_MODEL, RAGUnavailable
    # Translation is a retrieval aid, never a source of clinical facts.
    try:
        response = requests.post(f'{OLLAMA_BASE_URL}/api/chat', json={
            'model': OLLAMA_MODEL, 'stream': False,
            'messages': [{'role': 'system', 'content': 'Translate the Turkish question into English for medical literature search. Do not answer it. Preserve identifiers and medical terms. Return JSON with only the key query.'},
                         {'role': 'user', 'content': question}],
            'format': {'type':'object','properties':{'query':{'type':'string'}},'required':['query']},
            'options': {'temperature':0,'num_predict':160}}, timeout=(4,90))
        response.raise_for_status()
        query = json.loads(response.json()['message']['content'])['query']
        if not isinstance(query,str) or not query.strip():
            raise ValueError('Empty translation')
        return query[:1600]
    except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
        raise RAGUnavailable('Türkçe soru arama için çevrilemedi. Lütfen tekrar deneyin.') from exc


def turkish_local_answer(result):
    context = result.get('case_context')
    labels = {'Normal':'Normal','Benign':'İyi huylu','Malignant':'Kötü huylu',
              'Hip Bone':'Kalça kemiği','Upper Limb':'Üst ekstremite','Lower Limb':'Alt ekstremite',
              'frontal':'Önden','lateral':'Yandan','M':'Erkek','F':'Kadın','Male':'Erkek','Female':'Kadın'}
    paragraphs=[]
    if context:
        metadata=context['metadata']
        anatomy=', '.join(labels.get(x,x) for x in context['anatomical_location']) or 'belirtilmemiş'
        projection=', '.join(labels.get(x,x) for x in context['projection']) or 'belirtilmemiş'
        paragraphs.append(f"{context['case_id']} vakası {context['image_id']} kaynak görüntüsünü kullanır. BTXRD kaynak etiketi: {labels.get(context['source_label'],context['source_label'])}; alt tür: {context['source_subtype'] or 'belirtilmemiş'}. Anatomi: {anatomy}. Görüntüleme yönü: {projection}. Kaydedilen yaş: {metadata.get('age_years')}; cinsiyet: {labels.get(metadata.get('sex'),metadata.get('sex'))}. Kaynak yapılandırılmış üst veri içerir; klinik vaka anlatısı bulunmaz. [CASE]")
        model=context.get('model_analysis')
        if model:
            paragraphs.append(f"Model tahmini: {labels.get(model.get('prediction'),model.get('prediction'))}. Kalibre edilmemiş skor: %{100*model.get('confidence',0):.1f}. Model sürümü: {model.get('model_version')}.")
        else:
            paragraphs.append('Model tahmini ve bu görüntüye ait Grad-CAM için Vakayı analiz et düğmesine basın.')
    else:
        paragraphs.append('Bu açıklamayı bir tahminle ilişkilendirmek için bir vaka seçip analiz edin.')
    if any(x['citation_id']=='CAM' for x in result['citations']):
        paragraphs.append('Grad-CAM, tahmin edilen sınıfa göre göreli pozitif katkıyı gösterir. Koyu mor/siyah düşük, turuncu orta, parlak sarı yüksek katkı anlamına gelir. Ölçek her görüntü için ayrı normalize edilir. [CAM] Normal tahmininde parlak alanlar Normal sınıfının skorunu destekler. Renkler tümör varlığını, sınırını, şiddetini veya piksel başına olasılığı göstermez. Bindirme, bu kaba katkı haritasını radyografinin üzerine yerleştirir. Asistan yalnızca yapılandırılmış sonuçları alır; görüntü piksellerinden anatomik bulgu belirleyemez.')
    return {**result, 'answer':'\n\n'.join(paragraphs), 'notice':'Yalnızca araştırma amaçlıdır. Görüntü pikselleri dil modeline verilmez.'}
