# Country SDG

This is a Django project that displays information about the Sustainable Development Goals (SDGs) for different countries. The project uses data from the Sustainable Development Report and SDG Index, and also fetches news articles related to the selected country and SDGs using the News API.

## What is SDG?

The Sustainable Development Goals (SDGs) are a collection of 17 global goals set by the United Nations General Assembly in 2015. They are part of the 2030 Agenda for Sustainable Development, which aims to end poverty, protect the planet, and ensure prosperity for all by 2030. Each goal has specific targets to be achieved over the next 15 years.

## SDG Goals

1. **No Poverty**: End poverty in all its forms everywhere.
2. **Zero Hunger**: End hunger, achieve food security and improved nutrition, and promote sustainable agriculture.
3. **Good Health and Well-being**: Ensure healthy lives and promote well-being for all at all ages.
4. **Quality Education**: Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all.
5. **Gender Equality**: Achieve gender equality and empower all women and girls.
6. **Clean Water and Sanitation**: Ensure availability and sustainable management of water and sanitation for all.
7. **Affordable and Clean Energy**: Ensure access to affordable, reliable, sustainable, and modern energy for all.
8. **Decent Work and Economic Growth**: Promote sustained, inclusive, and sustainable economic growth, full and productive employment, and decent work for all.
9. **Industry, Innovation, and Infrastructure**: Build resilient infrastructure, promote inclusive and sustainable industrialization, and foster innovation.
10. **Reduced Inequality**: Reduce inequality within and among countries.
11. **Sustainable Cities and Communities**: Make cities and human settlements inclusive, safe, resilient, and sustainable.
12. **Responsible Consumption and Production**: Ensure sustainable consumption and production patterns.
13. **Climate Action**: Take urgent action to combat climate change and its impacts.
14. **Life Below Water**: Conserve and sustainably use the oceans, seas, and marine resources for sustainable development.
15. **Life on Land**: Protect, restore, and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss.
16. **Peace, Justice, and Strong Institutions**: Promote peaceful and inclusive societies for sustainable development, provide access to justice for all, and build effective, accountable, and inclusive institutions at all levels.
17. **Partnerships for the Goals**: Strengthen the means of implementation and revitalize the global partnership for sustainable development.

## Installation

1. **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/your-repo-name.git
    cd your-repo-name
    ```

2. **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

3. **Activate the virtual environment:**
    - On Windows:
        ```bash
        venv\Scripts\activate
        ```
    - On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```

4. **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5. **Apply the migrations:**
    ```bash
    python manage.py migrate
    ```

6. **Run the development server:**
    ```bash
    python manage.py runserver
    ```

7. **Open your web browser and visit:**
    ```
    http://127.0.0.1:8000/
    ```

Now you should be able to see the project running locally.
