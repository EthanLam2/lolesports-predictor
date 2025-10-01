import streamlit as st
from predictor import LolPredictor

st.set_page_config(
    page_title="LoL Match Predictor", 
    layout="centered"
)

st.markdown("""
<style>  
    /* Remove top padding from main container */
    .main .block-container {
        padding-top: 0rem;
        margin-top: 0rem;
    }
    
    /* Remove any extra spacing */
    .stApp {
        margin-top: -80px;
    }
    
    /* Remove default margins */
    .main {
        padding: 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_predictor():
    return LolPredictor()

def main():
    predictor = load_predictor()

    # get all possible inputs
    teams = predictor.get_teams()
    regions = predictor.get_regions()
    patches = predictor.get_patches()
    

    with st.sidebar:
        st.header("Match Info")
    
        selected_region = st.selectbox("Region", regions)
        selected_patch = st.selectbox("Patch #", patches, index=len(patches)-1)
    
    col_blue, col_red = st.columns(2)

    with col_blue:
        st.subheader("Blue Side")
        blue_team_name = st.selectbox("Select Blue Team", teams, key="blue_team")

    with col_red:
        st.subheader("Red Side") 
        available_red_teams = [team for team in teams if team != blue_team_name]

        # get current red team selection
        current_red_team = st.session_state.get("red_team", available_red_teams[0])
        
        # only reset if the current selection is no longer available
        if current_red_team not in available_red_teams:
            # default to 0 if not blue team
            default_index = 0
        else:
            # keep current selection
            default_index = available_red_teams.index(current_red_team)

        
        red_team_name = st.selectbox("Select Red Team",available_red_teams, key="red_team",index=default_index
    )
    

    st.markdown("---")

    # initialize variables
    roles = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]
    blue_players = {}
    blue_champions = {}
    red_players = {}
    red_champions = {}

    # get all players from blue and red team
    blue_team_players = predictor.get_team_players(blue_team_name)
    red_team_players = predictor.get_team_players(red_team_name)


    
    for role in roles:
        # separate blue and red column with a role column
        col_blue, col_role, col_red = st.columns([3, 1, 3])
        
        with col_role:
            st.markdown(f"**{role}**")
            st.write("")  
        
        
        with col_blue:
            # player and champion in sub columns
            player_col, champ_col = st.columns(2)
            
            with player_col:
                player_options = blue_team_players.get(role, []) + ["Custom Input"]
                selected_player = st.selectbox(
                    "Player", player_options, key=f"blue_{role}_player_select", label_visibility="collapsed"  
                )
                
                if selected_player == "Custom Input":
                    blue_players[role] = st.text_input("Enter Player Name:",key=f"blue_{role}_player_custom",placeholder="Player Name"
                    )
                else:
                    blue_players[role] = selected_player
            
            with champ_col:
                champion_options = predictor.get_champions(role) + ["Custom Input"]
                selected_champion = st.selectbox("Champion",champion_options,key=f"blue_{role}_champion_select", label_visibility="collapsed"  # Hide label
                )
                
                if selected_champion == "Custom Input":
                    blue_champions[role] = st.text_input("Enter Champion Name:", key=f"blue_{role}_champion_custom", placeholder="Champion Name"
                    )
                else:
                    blue_champions[role] = selected_champion
        
       
        with col_red:
            # player and champion in sub columns
            champ_col, player_col = st.columns(2)
            
            with player_col:
                player_options = red_team_players.get(role, []) + ["Custom Input"]
                selected_player = st.selectbox("Player",player_options, key=f"red_{role}_player_select",label_visibility="collapsed"  # Hide label
                )
                
                if selected_player == "Custom Input":red_players[role] = st.text_input("Enter Player Name:", key=f"red_{role}_player_custom",placeholder="Player Name"
                    )
                else:
                    red_players[role] = selected_player
            
            with champ_col:
                champion_options = predictor.get_champions(role) + ["Custom Input"]
                selected_champion = st.selectbox("Champion", champion_options, key=f"red_{role}_champion_select", label_visibility="collapsed"  # Hide label
                )
                
                if selected_champion == "Custom Input":
                    red_champions[role] = st.text_input("Enter Champion Name:", key=f"red_{role}_champion_custom", placeholder="Champion Name"
                    )
                else:
                    red_champions[role] = selected_champion
        
        st.write("")

    # prediction Button
    if st.button(" PREDICT MATCH OUTCOME", type="primary", use_container_width=True):
        
        # create team dictionaries
        blue_team_dict = {
            "team_name": blue_team_name,
            "players": blue_players,
            "champions": blue_champions 
        }
        
        red_team_dict = {
            "team_name": red_team_name,
            "players": red_players,
            "champions": red_champions 
        }
        
        # create match info using predictor function
        match_info = predictor.create_match_info(
            patch=float(selected_patch),
            region=selected_region,
            blue_team=blue_team_dict,
            red_team=red_team_dict
        )
        
        # make predictions
        voting_result = predictor.predict_voting(match_info)
        elastic_result = predictor.predict_elastic(match_info)
        
        # display Results
        st.write("<div style='text-align: center;'>Prediction Results</div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        # voting ensemble model
        with col1:
            st.subheader("Voting Ensemble")
            winner = voting_result["predicted_winner"]
            blue_prob = voting_result["blue_win_probability"]
            red_prob = 1 - blue_prob
            
            if winner == "Blue":
                st.info(f"{blue_team_name.upper()} predicted to win")
                st.metric("Winner Probability", f"{blue_prob:.1%}")

            else:
                st.error(f"{red_team_name.upper()} predicted to win")
                st.metric("Winner Probability", f"{red_prob:.1%}")
                
        # elastic net model
        with col2:
            st.subheader("Elastic Net")
            winner_e = elastic_result["predicted_winner"]
            blue_prob_e = elastic_result["blue_win_probability"]
            red_prob_e = 1 - blue_prob_e
            
            if winner_e == "Blue":
                st.info(f"{blue_team_name.upper()} predicted to win")
                st.metric("Winner Probability", f"{blue_prob_e:.1%}")
                
            else:
                st.error(f"{red_team_name.upper()} predicted to win")
                st.metric("Winner Probability", f"{red_prob_e:.1%}")
                
                

if __name__ == "__main__":
    main()