import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import os


# --- CONFIGURATION ---
st.set_page_config(page_title="Dashboard Immobilier Notaires", layout="wide")

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data():
    # On récupère le chemin du dossier où se trouve ce script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # On construit le chemin complet vers le fichier CSV
    file_path = os.path.join(current_dir, 'dataset_final.csv')
    
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"Fichier introuvable au chemin : {file_path}")
        return pd.DataFrame() 

    mapping_regions = {
        'Paris': 'Île-de-France', 'Marseille': 'PACA', 'Nice': 'PACA',
        'Lyon': 'Auvergne-Rhône-Alpes', 'Toulouse': 'Occitanie',
        'Montpellier': 'Occitanie', 'Bordeaux': 'Nouvelle-Aquitaine',
        'Lille': 'Hauts-de-France', 'Rennes': 'Bretagne', 'Rouen': 'Normandie'
    }
    df['Region'] = df['Ville_Recherche'].map(mapping_regions)
    return df

df = load_data()

# --- BARRE LATÉRALE ---
st.sidebar.header("🔍 Filtres")

# 1. Filtres Géographiques
with st.sidebar.expander("📍 Localisation", expanded=True):
    choix_reg = st.multiselect("Régions", sorted(df['Region'].unique()))
    
    # Logique pour filtrer les villes selon la région
    if choix_reg:
        villes_dispo = sorted(df[df['Region'].isin(choix_reg)]['Ville_Recherche'].unique())
    else:
        villes_dispo = sorted(df['Ville_Recherche'].unique())
        
    choix_ville = st.multiselect("Villes", villes_dispo)

# 2. Filtres Budget & Surface
with st.sidebar.expander("💰 Budget & Surface", expanded=True):

    # --- BUDGET ---
    st.write("Budget (€)")
    col1, col2 = st.columns(2)
    with col1:
        p_min = st.number_input("Min €", min_value=0, value=0, step=10000)
    with col2:
        # On met la valeur max par défaut
        max_price_def = int(df['Prix'].max())
        p_max = st.number_input("Max €", min_value=0, value=max_price_def, step=10000)

    st.divider() # Petite ligne de séparation

    # --- SURFACE ---
    st.write("Surface (m²)")
    col3, col4 = st.columns(2)
    with col3:
        s_min = st.number_input("Min m²", min_value=0, value=0, step=5)
    with col4:
        max_surf_def = int(df['Surface_m2'].max())
        s_max = st.number_input("Max m²", min_value=0, value=max_surf_def, step=5)

# 3. Filtre Pièces 
with st.sidebar.expander("🏠 Configuration", expanded=True):
    # On récupère les valeurs uniques de pièces triées
    pieces_dispo = sorted(df['Pieces'].unique())
    choix_pieces = st.multiselect("Nombre de pièces", pieces_dispo, default=pieces_dispo)

# --- APPLICATION DES FILTRES ---

# 1. Filtres numériques
df_filtered = df[
    (df['Prix'].between(p_min, p_max)) & 
    (df['Surface_m2'].between(s_min, s_max))
]

# 2. Filtre Géographique
if choix_reg: 
    df_filtered = df_filtered[df_filtered['Region'].isin(choix_reg)]
if choix_ville: 
    df_filtered = df_filtered[df_filtered['Ville_Recherche'].isin(choix_ville)]

# 3. Filtre Pièces
if choix_pieces:
    df_filtered = df_filtered[df_filtered['Pieces'].isin(choix_pieces)]

# --- TITRE PRINCIPAL ---
st.title(" Analyse du Marché Immobilier")

# --- RÉSUMÉ MÉTHODOLOGIQUE ---
with st.expander(" Méthodologie et Problématique", expanded=True):
    st.markdown(f"""
    ### **Problématique**
    > **Comment le prix au mètre carré varie-t-il en fonction de la localisation, de la surface et du type de bien immobilier en France ?**

    ### **Démarche Technique**
    Pour répondre à cette question, nous avons mis en place une solution d'automatisation basée sur l'analyse des flux de données du site *Immobilier.notaires.fr* :
    * **Identification de la source** : Via l'inspecteur réseau du navigateur, nous avons isolé l'API interne (flux JSON) qui alimente les recherches du site.
    * **Extraction automatisée** : Un script Python interroge dynamiquement cette source via une double boucle (par métropole et par pagination).
    * **Collecte sélective** : Pour garantir une base de comparaison équitable, nous avons extrait **50 annonces conformes par ville**, après avoir filtré les données non pertinentes (surfaces < 9m², parkings, terrains).
    """)

# --- ONGLETS ---
tab1, tab2 = st.tabs([" Tableaux & Corrélation", " Analyses Visuelles & Carte"])

with tab1:
    st.header("I. Analyse des indicateurs clés")
    st.info("Cette section présente une vue tabulaire de la répartition et de la valorisation des biens.")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader(" Répartition par type")
        repartition = df_filtered.groupby(['Ville_Recherche', 'Type']).size().unstack(fill_value=0)
        st.dataframe(repartition, use_container_width=True)
        st.caption("Volume de biens disponibles par ville et catégorie.")

    with col_b:
        st.subheader(" Prix au m²")
        stats_m2 = df_filtered.groupby('Ville_Recherche')['Prix_m2'].agg(['mean', 'median']).rename(columns={'mean':'Moyenne', 'median':'Médiane'})
        st.dataframe(stats_m2.style.format("{:.0f} €"), use_container_width=True)
        st.caption("Prix moyen et médian au mètre carré par ville.")

    st.divider()
    st.subheader(" Prix par Type de logement")
    stats_type = df_filtered.groupby(['Ville_Recherche', 'Type'])['Prix'].agg(['mean', 'median'])
    st.dataframe(stats_type.style.format("{:.0f} €"), use_container_width=True)
    st.caption("Budget moyen et médian selon la nature du bien.")

    st.divider()
    
    # --- CORRÉLATION ---
    st.subheader("II. Analyse de la Corrélation Surface / Prix")
    st.markdown("**Formule de Pearson (calcul de la relation linéaire) :**")
    st.latex(r"r = \frac{\sum(x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum(x_i - \bar{x})^2 \sum(y_i - \bar{y})^2}}")
    
    if not df_filtered.empty:
        fig_corr = px.scatter(df_filtered, x="Surface_m2", y="Prix", trendline="ols", 
                             trendline_color_override="red", height=500)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        corr_val = df_filtered['Surface_m2'].corr(df_filtered['Prix'])
        st.write(f"### Coefficient de corrélation : **{corr_val:.2f}**")
        
        st.write(f"""
        **Interprétation du graphique :**
        1. **Relation Linéaire :** La droite rouge indique la tendance globale. Un coefficient de **{corr_val:.2f}** montre une corrélation {'forte' if corr_val > 0.7 else 'modérée'}.
        2. **Analyse du nuage :** Chaque point représente un bien. Plus ils sont proches de la ligne, plus la surface explique le prix.
        3. **Variabilité :** On observe des écarts verticaux importants, ce qui signifie qu'à surface égale, le prix peut varier du simple au double selon le quartier ou l'état.
        4. **Conclusion :** Si le prix augmente logiquement avec la taille, la localisation reste le paramètre qui fait 'sauter' les prix au-delà de la norme.
        """)
    else:
        st.warning("Aucune donnée pour les filtres sélectionnés.")

with tab2:
    if not df_filtered.empty:
        st.header("III. Visualisations de la distribution")

        # Boxplot
        st.subheader("1. Dispersion des prix par Région")
        st.plotly_chart(px.box(df_filtered, x="Region", y="Prix", color="Region", height=500), use_container_width=True)
        st.write("**Note sur le Boxplot :** Ce graphique permet d'identifier les zones les plus chères (boîtes les plus hautes) et les biens d'exception (points isolés appelés 'outliers').")

        st.divider()

        # Histogrammes
        st.subheader("2. Distribution des fréquences (Histogrammes par Région)")
        fig_hist = px.histogram(df_filtered, x="Prix", facet_col="Region", facet_col_wrap=2, 
                                color="Region", height=800)
        st.plotly_chart(fig_hist, use_container_width=True)
        st.write("""
        **Note sur les histogrammes :** Ces graphiques montrent la concentration des biens. Un pic très à gauche indique un marché avec beaucoup de petits prix (ex: province), 
        tandis qu'une courbe étalée vers la droite montre un marché diversifié avec des biens de luxe (ex: PACA ou Paris).
        """)

        st.divider()

        # Carte
        st.subheader("3. Carte interactive des prix")
        st.write("**Analyse géographique :** Passez la souris sur un point pour voir les détails.")
        
        # Centrer la carte
        m = folium.Map(location=[df_filtered['Latitude'].mean(), df_filtered['Longitude'].mean()], zoom_start=6)
        
        for _, row in df_filtered.iterrows():
            # --- CRÉATION DU TOOLTIP DÉTAILLÉ ---
            tooltip_content = f"""
            <b>Ville :</b> {row['Ville_Reelle']}<br>
            <b>Type :</b> {row['Type']}<br>
            <b>Prix :</b> {row['Prix']:,} €<br>
            <b>Surface :</b> {row['Surface_m2']} m²<br>
            <b>Pièces :</b> {row['Pieces']}
            """
            
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=6, 
                color='blue' if row['Type'] == 'Appartement' else 'red',
                fill=True, 
                fill_opacity=0.7,
                tooltip=tooltip_content
            ).add_to(m)
            
        st_folium(m, width=1200, height=600)
    else:
        st.error("Sélectionnez des filtres pour afficher les graphiques.")