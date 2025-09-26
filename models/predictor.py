import pandas as pd
import joblib

class LolPredictor:
    def __init__(self):
        self.load_data()

    # load encoders, models and model inputs
    def load_data(self):
        self.encoders = {
            "champion": joblib.load("champion_encoders.pkl"),
            "player": joblib.load("player_encoders.pkl"),
            "team": joblib.load("team_encoder.pkl"),
            "region": joblib.load("region_encoder.pkl"),
            "patch": joblib.load("patch_encoder.pkl")
        }
        self.final_team_elos = joblib.load("final_team_elos.pkl")
        self.feature_columns = joblib.load("feature_columns.pkl")
        self.voting_model = joblib.load("voting_ensemble_model.pkl")
        self.elastic_model = joblib.load("elastic_net_model.pkl")
        self.df_original = pd.read_csv("processed_historical_data.csv")
    
    def get_player_historical_stats(self, player_name, role):
        stat_columns = ["kills", "deaths", "assists", "kp%", "dmg%", "gd@15"]
        historical_stats = {}
        
        # get all games for this player in this role (from both blue and red sides)
        blue_player_col = f"blue_{role}_player"
        red_player_col = f"red_{role}_player"

        encoded_player = self.encoders["player"][f"{role}_player"].transform([player_name.lower()])[0]
        blue_games = self.df_original[self.df_original[f"blue_{role}_player"] == encoded_player]
        red_games = self.df_original[self.df_original[f"red_{role}_player"] == encoded_player]
        
        for stat in stat_columns:
            blue_stat_col = f"blue_{role}_{stat}"
            red_stat_col = f"red_{role}_{stat}"
            
            # combine stats from both blue and red games
            all_stat_values = []
            
            if len(blue_games) > 0:
                all_stat_values.extend(blue_games[blue_stat_col].tolist())
            if len(red_games) > 0:
                all_stat_values.extend(red_games[red_stat_col].tolist())
            if len(all_stat_values) == 0:
                # if no historical data use historical data
                blue_avg = self.df_original[blue_stat_col].mean()
                red_avg = self.df_original[red_stat_col].mean()
                historical_stats[stat] = (blue_avg + red_avg) / 2
            else:
                # calculate player"s historical average
                historical_stats[stat] = sum(all_stat_values) / len(all_stat_values)
        
        return historical_stats

    # gets their latest elo
    def get_team_elo(self, team_name):
        encoded_team = self.encoders["team"].transform([team_name.lower()])[0]
        return self.final_team_elos[encoded_team]

    
    def predict_match(self, match_info, model):
        prediction_data = {}
        
        # one hot encode the patch number
        patch_df = pd.DataFrame({"Patch": [match_info["patch"]]})
        patch_encoded = self.encoders["patch"].transform(patch_df)
        patch_features = self.encoders["patch"].get_feature_names_out(["Patch"])
        for i, feature_name in enumerate(patch_features):
            prediction_data[feature_name] = patch_encoded[0][i]
        
        # one hot encode the region
        region_df = pd.DataFrame({"Region": [match_info["region"].lower()]})
        region_encoded = self.encoders["region"].transform(region_df)
        region_features = self.encoders["region"].get_feature_names_out(["Region"])
        for i, feature_name in enumerate(region_features):
            prediction_data[feature_name] = region_encoded[0][i]
        
        # add team elo per team
        prediction_data["blue_team_elo_rating"] = self.get_team_elo(match_info["blue_team"]["team_name"])
        prediction_data["red_team_elo_rating"] = self.get_team_elo(match_info["red_team"]["team_name"])
        
        # encode teams, players and champions
        for team_color in ["blue", "red"]:
            team_data = match_info[f"{team_color}_team"]
            prediction_data[f"{team_color}_Team"] = self.encoders["team"].transform([team_data["team_name"].lower()])[0]
            
            for role in ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]:
                player_name = team_data["players"][role]
                champion_name = team_data["champions"][role]

                # encode players for each role
                prediction_data[f"{team_color}_{role}_player"] = self.encoders["player"][f"{role}_player"].transform([player_name.lower()])[0]
                # encode champions for each role
                prediction_data[f"{team_color}_{role}_champion"] = self.encoders["champion"][f"{role}_champion"].transform([champion_name.lower()])[0]

                # add historical average stats
                historical_stats = self.get_player_historical_stats(player_name, role)
                for stat, avg_value in historical_stats.items():
                    prediction_data[f"{team_color}_{role}_historical_avg_{stat}"] = avg_value
        
        # create prediction dataframe and wrape prediction_data
        pred_df = pd.DataFrame([prediction_data])
        pred_df = pred_df.reindex(columns=self.feature_columns, fill_value=0.0)
        
        # make prediction and get probability of blue team winning
        blue_win_prob = model.predict_proba(pred_df)[0][1]
        # assign winner if win prob > 0.5
        predicted_winner = "Blue" if blue_win_prob > 0.5 else "Red"

        
        return {
            "predicted_winner": predicted_winner, "blue_win_probability": blue_win_prob
        }
    
   
    def predict_voting(self, match_info):
        return self.predict_match(match_info, self.voting_model)
    
    def predict_elastic(self, match_info):
        return self.predict_match(match_info, self.elastic_model)
      

    # get all teams
    def get_teams(self):
        return sorted(self.encoders["team"].classes_)

    # get all champions for a specific role
    def get_champions(self, role):
        return sorted(self.encoders["champion"][f"{role}_champion"].classes_)
            
    # get all players for a specific role
    def get_players(self, role):
        return sorted(self.encoders["player"][f"{role}_player"].classes_)

    # get all players who have played for a specific team
    def get_team_players(self, team_name):
        encoded_team = self.encoders["team"].transform([team_name.lower()])[0]
        team_players = {}
        
        for role in ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]:
            # combine both blue and red games
            blue_players = set(self.df_original[self.df_original["blue_Team"] == encoded_team][f"blue_{role}_player"])
            red_players = set(self.df_original[self.df_original["red_Team"] == encoded_team][f"red_{role}_player"])
            
            all_players = blue_players | red_players
            decoded_players = [self.encoders["player"][f"{role}_player"].inverse_transform([p])[0] for p in all_players]
            team_players[role] = sorted(decoded_players)
        
        return team_players
    def get_regions(self):
        # get regions from one hot encoded columns
        region_columns = [col for col in self.df_original.columns if col.startswith('Region_')]
        # default region not one hot encoded
        regions = ['cn']
        
        # add regions that have been one-hot encoded
        for col in region_columns:
            region_name = col.replace('Region_', '')
            regions.append(region_name)
        
        return sorted(regions)

    def get_patches(self):
        # get patches from one hot encoded columns
        patch_columns = [col for col in self.df_original.columns if col.startswith('Patch_')]
        # default patch not one hot encoded
        patches = [15.1]
    
        # add patches that have one hot columns
        for col in patch_columns:
            patch_str = col.replace('Patch_', '')
            patch_float = float(patch_str)
            patches.append(patch_float)
        sorted_patches = sorted(patches, key=lambda x: (int(str(x).split('.')[0]), int(str(x).split('.')[1])), reverse = True)
        return sorted_patches

    def create_match_info(self, patch, region, blue_team, red_team):
        return {
            "patch": patch, "region": region, "blue_team": blue_team, "red_team": red_team
            }
            


def print_prediction(result, model_name):
        winner = result["predicted_winner"]
        blue_prob = result["blue_win_probability"]
        red_prob = 1 - blue_prob
        
        print(f"{model_name} Team:")
        print(f"Winner: {winner}")
        print(f"Blue win probability:{blue_prob:.1%} || Red win probability:{red_prob:.1%}")


if __name__ == "__main__":
    # initialize predictor
    predictor = LolPredictor()