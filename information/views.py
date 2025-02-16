from django.shortcuts import render
import pandas as pd
import os
from .constant import all_countries, landing_data
import math
from django.conf import settings
import matplotlib.pyplot as plt
import seaborn as sns
from newsapi import NewsApiClient
from django.http import JsonResponse
import json
import google.generativeai as genai


def home(request):
    return render(request, 'home.html', {'landing_data': landing_data,
                                         'all_countries': all_countries})

def info_score(request, country_name):
    sustainable_path = os.path.join(os.path.dirname(__file__), '../data/sustainable_development_report_2023.csv')
    df = pd.read_csv(sustainable_path)
    country = df[df['country'] == country_name].to_dict(orient='records')
    
    new_landing_data = landing_data.copy()
    for i in range(17):
        goal_key = f'goal_{i+1}_score'
        score = country[0].get(goal_key)  # Get the score value

        # Check if score is NaN before conversion
        if score is not None and not (isinstance(score, float) and math.isnan(score)):
            new_landing_data[i]['score'] = int(score)  # Convert to integer if valid
        else:
            new_landing_data[i]['score'] = "N/A"  
            
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    # Create the model
    generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
    system_instruction=f"""
    You are an objective research that assess country SDG based on you know and give recommendation 
    in 1 paragraph, the input will be country name and i will give you the score of SDG
    
    {json.dumps(new_landing_data)}
    
    
    """,
    )

    chat_session = model.start_chat(
    history=[
        {
        "role": "user",
        "parts": [
            "Assess the SDG 1 (End poverty in all its forms everywhere) for Afghanistan",
        ],
        },
        {
        "role": "model",
        "parts": [
            "Okay, I can provide an assessment of SDG 1 (No Poverty) in Afghanistan based on available data and reports from reputable sources like the UN, World Bank, and other international organizations.  It's important to note that the situation in Afghanistan is highly complex and fluid, especially since the political changes in 2021.  Therefore, this assessment is based on the best available information, but might not reflect the very latest developments in full detail.\n\n**Assessment of SDG 1 in Afghanistan:**\n\nAfghanistan faces immense challenges in achieving SDG 1 and has consistently struggled with high poverty rates even before recent events. The current situation has significantly worsened the prospects for achieving this goal.\n\n**Here's a breakdown of the key factors:**\n\n*   **Baseline Poverty Levels (Pre-2021):**  Prior to the Taliban takeover in August 2021, Afghanistan already had very high poverty rates. Estimates varied, but generally around half the population lived below the national poverty line. This was due to decades of conflict, weak governance, corruption, limited economic opportunities, and a heavy reliance on foreign aid.\n\n*   **Impact of Conflict and Instability:**  The protracted conflict has been a major driver of poverty. It has disrupted livelihoods, displaced populations, destroyed infrastructure, and limited access to essential services like healthcare and education.\n\n*   **Economic Crisis:**  Following the political transition in 2021, Afghanistan's economy has experienced a severe contraction. The suspension of international aid, the freezing of Afghan assets abroad, and the disruption of trade have all contributed to this crisis. Unemployment has soared, and many businesses have closed.\n\n*   **Humanitarian Crisis:**  The economic crisis has fueled a severe humanitarian crisis, with widespread food insecurity and malnutrition. Millions of people are in need of humanitarian assistance. This further exacerbates poverty and vulnerability.\n\n*   **Displacement:** Internal displacement and refugee flows have increased due to conflict, insecurity, and economic hardship. Displaced populations are particularly vulnerable to poverty.\n\n*   **Gender Inequality:**  Women and girls face significant barriers to economic participation and access to education and healthcare, further increasing their vulnerability to poverty. Restrictions imposed on women's rights since 2021 have worsened the situation.\n\n*   **Lack of Social Protection:**  Social safety nets and social protection programs are weak in Afghanistan, leaving many people without adequate support to cope with poverty.\n\n*   **Data limitations:** Collecting accurate data on poverty rates is difficult because of the security situation, geographic inaccessibility and the capacity of governmental institutions.\n\n**Specific SDG 1 Targets and Afghanistan's Progress (or Lack Thereof):**\n\n*   **SDG 1.1 (Eradicate extreme poverty for all people everywhere):**  Afghanistan is very far from achieving this target.  Extreme poverty has likely increased significantly since 2021.\n\n*   **SDG 1.2 (Reduce at least by half the proportion of men, women and children of all ages living in poverty in all its dimensions according to national definitions):**  The opposite is happening; poverty is increasing.\n\n*   **SDG 1.3 (Implement nationally appropriate social protection systems and measures for all):**  Social protection systems are weak and inadequate to address the scale of poverty.\n\n*   **SDG 1.4 (Ensure that all men and women, in particular the poor and the vulnerable, have equal rights to economic resources, as well as access to basic services, ownership and control over land and other forms of property, inheritance, natural resources, appropriate new technology and financial services):**  Progress on this target is severely hampered by conflict, insecurity, and discrimination.\n\n*   **SDG 1.5 (Build the resilience of the poor and those in vulnerable situations and reduce their exposure and vulnerability to climate-related extreme events and other economic, social and environmental shocks and disasters):**  Afghanistan is highly vulnerable to climate change and natural disasters, further increasing the vulnerability of the poor.\n\n**Overall Conclusion:**\n\nAfghanistan faces immense challenges in achieving SDG 1. The situation has deteriorated significantly since 2021 due to the economic crisis, humanitarian crisis, and ongoing instability.  Achieving SDG 1 will require a multi-faceted approach that addresses the root causes of poverty, including conflict, weak governance, inequality, and climate vulnerability.  It will also require sustained international support and a commitment to inclusive development. The current political climate makes the achievment of SDG1 extremely unlikely in the near future.\n\n**Disclaimer:** This assessment is based on publicly available information and reflects the general consensus among international organizations. The situation is constantly evolving, and new data may emerge that could alter this assessment.",
        ],
        },
        {
        "role": "user",
        "parts": [
            "Assess the SDG 1 (End poverty in all its forms everywhere) for Afghanistan and summary it make it only one paragraph\n",
        ],
        },
        {
        "role": "model",
        "parts": [
            "Afghanistan faces extreme challenges in achieving SDG 1, with poverty rates already high before 2021 and significantly worsened by the subsequent political transition, economic collapse, and humanitarian crisis. Conflict, instability, and climate vulnerability exacerbate the situation, while limited social protection systems and gender inequality further hinder progress. Millions face food insecurity, and the erosion of women's rights impedes economic development. Consequently, Afghanistan is far from eradicating extreme poverty or even reducing overall poverty rates, making the attainment of SDG 1 highly unlikely without substantial, sustained international support and a concerted effort to address the root causes of poverty in a volatile and uncertain environment.\n",
        ],
        },
    ]
    )

    response = chat_session.send_message(country_name)

    visualization_path = os.path.join(os.path.dirname(__file__), '../data/sdg_index_2000-2022.csv')

    df_visualization = pd.read_csv(visualization_path)

    # Filter data for selected country
    country_visualization = df_visualization[df_visualization['country'] == country_name]

    if country_visualization.empty:
        return JsonResponse({"error": "No data found for this country"}, status=404)

    goal_columns = [col for col in df_visualization.columns if 'goal_' in col]

    data_json = country_visualization.to_dict(orient="records")
    
    newsapi = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))
    
    top_news = newsapi.get_everything(
    q=(
        f'"{country_name}" AND ('
        '"United Nations" OR "UN" OR "SDG" OR "Sustainable Development Goals" OR '
        '"climate action" OR "zero hunger" OR "no poverty" OR "quality education" OR "good health" OR '
        '"clean energy" OR "gender equality" OR "economic growth" OR "sustainability" OR '
        '"environmental protection" OR "climate change" OR "renewable energy" OR "innovation")'
    ),
    language='en',
    sort_by='relevancy',)

    list_of_news = []
    for article in top_news['articles'][:10]:
        data = {}
        data['title'] = article['title']
        data['source'] = article['source']['name']
        data['url'] = article['url']
        data['description'] = article['description']
        data['image'] = article['urlToImage']    
        list_of_news.append(data)
    
    return render(request, 'info_score.html',
                  {
                    'landing_data': new_landing_data,
                    'all_countries': all_countries,
                    "sdg_data": json.dumps(data_json),  # ✅ Ensure proper JSON formatting
                    "goal_columns": json.dumps(goal_columns),  # ✅ Ensure proper JSON formatting
                    "country_name": country_name,
                    "relevant_news": list_of_news,
                    "ai_response": response.text
                    })