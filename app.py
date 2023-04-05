from flask import Flask,make_response,request
from pymongo import MongoClient,UpdateOne
import random
from bson import json_util,ObjectId
import json
from flask_cors import CORS
import urllib.parse
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

url = "https://fantasy.iplt20.com/season/services/feed/live/player/stats?liveVersion=11"

headers = {
   "referer": "https://fantasy.iplt20.com/season/stats/playerstats/points",
    "Content-Type":"application/json; charset=utf-8",
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"

}

client = MongoClient("mongodb+srv://efladmin:god_is_watching@cluster0.eezohvz.mongodb.net/?retryWrites=true&w=majority")

db=client["efl2023"]

collections = db["eflCricket"]

ownercollection = db["eflCricketOwners"]

#collections = db["playersCopy"]

#ownercollection = db["ownersCopy"]

@app.route("/")
def welcome():
    return "Welcome to EFL2023"

@app.route('/getallplayers', methods=["GET"])
def get_all_players():
    players = []
    cursor = collections.find()
    for player in cursor:
        players.append(player)
    return json.loads(json_util.dumps(players))

@app.route('/getallsoldplayers', methods=["GET"])
def get_all_sold_players():
    soldplayers = []
    mystatusquery = {"status":"sold"}
    cursor = collections.find(mystatusquery)
    for allsoldplayer in cursor:
        soldplayers.append(allsoldplayer)
    return json.loads(json_util.dumps(soldplayers))

@app.route('/getspecificplayer/<name>', methods=["GET"])
def get_a_player(name):
    name = urllib.parse.unquote(name)
    player_query = {"name":{"$regex":name,"$options" :'i'}}
    player_data = collections.find_one(player_query)
    if player_data:
        return json.loads(json_util.dumps(player_data))
    else:
        return json.loads(json_util.dumps("player not found"))

@app.route('/getallownersdata', methods=["GET"])
def get_all_owners():
    owners = []
    cursor = ownercollection.find()
    for owner in cursor:
        owners.append(owner)
    return json.loads(json_util.dumps(owners))

@app.route('/getplayer', methods=["GET"])
def get_player():
    tier1 = []
    tier2 = []
    tier3 = []
    tier4 = []
    cursor = collections.find()
    for item in cursor:
        if item['tier'] == 1 and item['status']=="unsold":
            tier1.append(item)
        elif item['tier'] == 2 and item['status']=="unsold":
            tier2.append(item)
        elif item['tier'] == 3 and item['status']=="unsold":
            tier3.append(item)
        elif item['tier'] == 4 and item['status']=="unsold":
            tier4.append(item)
    if len(tier1) > 0:
        pick = random.choice(tier1)
    elif len(tier2) > 0:
        pick = random.choice(tier2)
    elif len(tier3) > 0:
        pick =random.choice(tier3)
    elif len(tier4) > 0:
        pick =random.choice(tier4)
    else:
        print("All players are processed")
    
    return json.loads(json_util.dumps(pick))

@app.route('/updateplayer/<_id>',methods=['PUT'])
def update_player(_id):

    updated_data = request.get_json()
    
    filter = {"_id": ObjectId(str(_id))}
   
    result = collections.update_one(filter, {"$set": updated_data})
    
    #code to handle second owner update
    if updated_data['status'] == "sold":
        owner_team = updated_data['ownerTeam']
        #Adding below code for mock auction
        #player_points = updated_data['points']

        myquery = {"ownerName":owner_team}

        owners_data = ownercollection.find(myquery)

        for owner_items in owners_data:
           
            owner_items["currentPurse"] = owner_items["currentPurse"] - int(updated_data["boughtFor"])
            owner_items["totalCount"] = owner_items["totalCount"] + 1
            owner_items["maxBid"] = owner_items["currentPurse"] - (35 * (15-owner_items["totalCount"]))
            if updated_data["role"] == "Batter":
                owner_items["batCount"] = owner_items["batCount"] + 1
            elif updated_data["role"] == "Bowler":
                owner_items["ballCount"] = owner_items["ballCount"] + 1
            elif updated_data["role"] == "Allrounder":
                owner_items["arCount"] = owner_items["arCount"] + 1
                #owner_items["ballCount"] = owner_items["ballCount"] + 1
            elif updated_data["role"] == "WK-Batter":
                owner_items["batCount"] = owner_items["batCount"] + 1
                owner_items["wkCount"] = owner_items["wkCount"] + 1
            else:
                print("Role not found")
            
            if updated_data["country"] != "India":
                owner_items["fCount"] = owner_items["fCount"] + 1

        filter_owner = {"_id": ObjectId(str(owner_items["_id"]))}
        result_owner = ownercollection.update_one(filter_owner, {"$set": owner_items})
   
    return json_util.dumps(result.raw_result)

def generate_objects(input_arr, purse, mbid):
    output_arr = []

    for owner_name in input_arr:
        obj = {
            "ownerName": owner_name,
            "totalPoints": 0,
            "batCount": 0,
            "ballCount": 0,
            "wkCount": 0,
            "fCount": 0,
            "totalCount": 0,
            "currentPurse": purse,
            "maxBid": mbid,
            "arCount": 0,
            "standing":[0]
        }
        output_arr.append(obj)

    return output_arr


@app.route('/setup', methods=['POST'])
def setup():
    # create owners table
    input_json = request.get_json()
    objects = generate_objects(
        input_json["teamNames"], input_json["purse"], input_json["mbid"])
    ownercollection.drop()
    resultowner = ownercollection.insert_many(objects)
    print(resultowner)
    

    # reset players table
    result = collections.update_many(
        {}, {"$set": {"ownerTeam": "", "boughtFor": 0, "status": "unsold","points":0}})
    return json_util.dumps(result.raw_result)
@app.route('/deleteplayer/<_id>',methods=['PUT'])
def delete_player(_id):

    delete_data = request.get_json()
    #return(delete_data)
    
    idfilter = {"_id": ObjectId(str(_id))}

    amount = delete_data["boughtFor"]
    owner_team = delete_data["ownerTeam"]
    #player_points = delete_data['points']
    delete_data["boughtFor"] = 0
    delete_data["ownerName"] =""
    #delete_data["points"] = 0
    
    

    result = collections.update_one(idfilter, {"$set": delete_data})
    #code to handle  owner db update
    #owner_team = delete_data['ownerTeam']
    #Adding below code for mock auction
    #player_points = delete_data['points']

    myquery = {"ownerName":owner_team}

    owners_data = ownercollection.find(myquery)

    for owner_items in owners_data:
            #Adding below code for mock auction
        #owner_items["totalPoints"] =  owner_items["totalPoints"] - player_points
            
        owner_items["currentPurse"] = owner_items["currentPurse"] + int(amount)
        owner_items["totalCount"] = owner_items["totalCount"] - 1
        owner_items["maxBid"] = owner_items["currentPurse"] - (35 * (15-owner_items["totalCount"]))
        if delete_data["role"] == "Batter":
            owner_items["batCount"] = owner_items["batCount"] - 1
        elif delete_data["role"] == "Bowler":
            owner_items["ballCount"] = owner_items["ballCount"] - 1
        elif delete_data["role"] == "Allrounder":
            owner_items["arCount"] = owner_items["arCount"] - 1
                #owner_items["ballCount"] = owner_items["ballCount"] + 1
        elif delete_data["role"] == "WK-Batter":
            owner_items["batCount"] = owner_items["batCount"] - 1
            owner_items["wkCount"] = owner_items["wkCount"] - 1
        else:
            print("Role not found")
            
        if delete_data["country"] != "India":
            owner_items["fCount"] = owner_items["fCount"] - 1

        filter_owner = {"_id": ObjectId(str(owner_items["_id"]))}
        result_owner = ownercollection.update_one(filter_owner, {"$set": owner_items})
    return json_util.dumps(result.raw_result)


@app.route('/updatescores', methods=['POST'])
def updatescores():
    count = 0
    totalcount = 0
    response = requests.get(url, headers=headers)

    # storing the JSON response 
    # from url in data
    data_json = json.loads(response.text)
    playersdata ={}
    playersdata = data_json["Data"]["Value"]["PlayerStats"]

    players_name = list(map(lambda rec: rec.get('plyrnm'), playersdata))
    players_points = list(map(lambda rec: rec.get('ovrpoint'), playersdata))
    
    totalcount = len(players_name)

    ownersdata_cursor = ownercollection.find()

    owner_to_points_start = {}
    for owner in ownersdata_cursor:
        owner_to_points_start[owner["ownerName"]] = 0


    for index in range(len(players_name)):
        myquery = {"name":players_name[index]}

        player_data = collections.find(myquery)

        for player in player_data:
            #print(player)
            player["points"] = int(players_points[index])
            if player["ownerTeam"] != "":
                owner_to_points_start[player["ownerTeam"]] +=player["points"]

            filter = {"_id": ObjectId(str(player["_id"]))}
            result = collections.update_one(filter, {"$set": player})

            #count += 1
    
    update_ownersdata_cursor = ownercollection.find()            

    for curowner in update_ownersdata_cursor:
        curowner["totalPoints"] = owner_to_points_start[curowner["ownerName"]]

        filter_owner = {"_id": ObjectId(str(curowner["_id"]))}
        result_owner = ownercollection.update_one(filter_owner, {"$set": curowner})
        #result_count = [count,totalcount]
    return json_util.dumps(result.raw_result)

'''
@app.route('/updatestandings', methods=['POST'])
def updatestandings():
    ownersdata_cursor = ownercollection.find()

    
    owner_to_points ={}
    for owner in ownersdata_cursor:
        owner_to_points[owner["ownerName"]] = owner["totalPoints"]

    sorted_teams = sorted(owner_to_points.items(), key=lambda x: x[1], reverse=True)

    # create a new dictionary to store standings
    standings = {}
    rank = 1
    prev_points = None
    for idx, team in enumerate(sorted_teams):
        team_name = team[0]
        points = team[1]
        if prev_points is None or points < prev_points:
            standings[team_name] = rank
            rank +=  1
        else:
            standings[team_name] = rank-1
        prev_points = points

    stand_update_ownersdata_cursor = ownercollection.find()            

    for currowner in stand_update_ownersdata_cursor:
        currowner["standing"].append(standings[currowner["ownerName"]])
    
        filter_owner = {"_id": ObjectId(str(currowner["_id"]))}
        result_owner = ownercollection.update_one(filter_owner, {"$set": currowner})

    return json_util.dumps(result_owner.raw_result)
    
    '''



@app.route('/replaceplayer/<_id>', methods=['PUT'])
def replace_player(_id):

    input_data = request.get_json()
    
    inPlayer = input_data['inPlayer']
    inPlayerrole = input_data['inPlayerrole']
    inPlayernationality = input_data['inPlayernationality']
    outPlayer = input_data['outPlayer']
    outPlayerrole =input_data['outPlayerrole']
    outPlayernationality =input_data['outPlayernationality']
    replacementDate =input_data['replacementDate']
    pointsToDeduct =input_data['pointsToDeduct']

    replacement_data={"inPlayer":inPlayer,"outPlayer":outPlayer,"replacementDate":replacementDate,"pointsToDeduct":pointsToDeduct}
    #print(replacement_data)
    
    ownercollection.update_one(
        { "_id": ObjectId(str(_id)) }, 
        { "$push": { "replacementsHistory": replacement_data } }
    )
    
    filter_owner = {"_id": ObjectId(str(_id))}
    get_ownersdata = ownercollection.find(filter_owner)
    
    for team in get_ownersdata:
        teamname = team['ownerName']
        
        if outPlayerrole == "Batter" :
            team["batCount"] = team["batCount"] - 1
        elif outPlayerrole == "Bowler":
            team["ballCount"] = team["ballCount"] - 1
        elif outPlayerrole == "Allrounder":
            team["arCount"] = team["arCount"] - 1
                #owner_items["ballCount"] = owner_items["ballCount"] + 1
        elif outPlayerrole == "WK-Batter":
            team["batCount"] = team["batCount"] - 1
            team["wkCount"] = team["wkCount"] - 1
       
        if inPlayerrole == "Batter" :
            team["batCount"] = team["batCount"] + 1
        elif inPlayerrole == "Bowler":
            team["ballCount"] = team["ballCount"] + 1
        elif inPlayerrole == "Allrounder":
            team["arCount"] = team["arCount"] + 1
                #owner_items["ballCount"] = owner_items["ballCount"] + 1
        elif inPlayerrole == "WK-Batter":
            team["batCount"] = team["batCount"] + 1
            team["wkCount"] = team["wkCount"] + 1

        if outPlayernationality != 'India' :
            team["fCount"] = team["fCount"] - 1
        
        if inPlayernationality != 'India' :
            team["fCount"] = team["fCount"] + 1
        

    
    result_owner = ownercollection.update_one(filter_owner, {"$set": team})


    myquery = {"name":inPlayer}

    player_data = collections.find(myquery)
    
    
    for player in player_data:
            player['ownerTeam'] = teamname
            player['status'] = "sold"
            #print(player)
            filter = {"_id": ObjectId(str(player["_id"]))}
            result = collections.update_one(filter, {"$set": player})
    

    # Return a success response
    return json_util.dumps({ "status": "success", "message": "Player replacement added successfully." })




''''''''''''

def get_player_scores(playersdata):
    player_scores = {}
    for player in playersdata:
        player_name = player['plyrnm']
        player_score = int(player['ovrpoint'])
        player_scores[player_name] = player_score
    return player_scores


def extract_replacement_history(collection):
    # Create an empty dictionary to store the results
    result_dict = {}

    # Loop through all documents in the collection
    for doc in collection.find():

        # Extract the replacementHistory array from the document
        replacement_history = doc.get("replacementsHistory")
        print(len(replacement_history))
        # If the replacementHistory array exists and is not empty
        if replacement_history and len(replacement_history) > 0:

            # Loop through each element in the replacementHistory array
            for history in replacement_history:

                # Extract the inPlayer and pointsToDeduct values
                in_player = history.get("inPlayer")
                points_to_deduct = history.get("pointsToDeduct")

                # If the inPlayer value exists and is not empty
                if in_player:

                    # Add the inPlayer and pointsToDeduct values to the result dictionary
                    if in_player not in result_dict:
                        result_dict[in_player] = points_to_deduct
                        print(in_player, points_to_deduct)

    # Return the result dictionary
    return result_dict


def deduct_points(player_scores, player_points_to_deduct):
    for player, points in player_points_to_deduct.items():
        if player in player_scores:
            player_scores[player] -= points
    return player_scores


def get_formatted_timestamp():
    # Get the current date and time
    now = datetime.now()

    # Format the timestamp string
    timestamp_str = now.strftime("%B %d, %Y at %I:%M%p").replace(" 0", " ")
    return timestamp_str

@app.route('/updatescores', methods=['POST'])
def updateScores():
    sold_players = collections.find({"status": "sold"})

    sold_players_dict = {}
    for player in sold_players:
        sold_players_dict[player["name"]] = player

    response = requests.get(url, headers=headers)

    # storing the JSON response
    # from url in data
    data_json = json.loads(response.text)
    playersdata = {}
    playersdata = data_json["Data"]["Value"]["PlayerStats"]

    player_scores = get_player_scores(playersdata)
    player_points_to_deduct = extract_replacement_history(ownercollection)
    player_scores = deduct_points(player_scores, player_points_to_deduct)

    # BULK UPDATE PLAYER POINTS
    update_ops = []
    for player_name, player_score in player_scores.items():
        update_op = UpdateOne(
            {"name": player_name},
            {"$set": {"points": player_score}}
        )
        update_ops.append(update_op)
    print(len(update_ops))
# Execute the bulk write operation
    result = collections.bulk_write(update_ops)

# Print the number of documents updated
    print("Number of documents updated:", result.matched_count)

    # UPDATE OWNERS POINTS
    ownersdata_cursor = ownercollection.find()

    owner_to_points_start = {}
    for owner in ownersdata_cursor:
        owner_to_points_start[owner["ownerName"]] = 0

    for playerName in sold_players_dict:
        playerPoints = player_scores[playerName]
        playerObj = sold_players_dict[playerName]
        ownerTeam = playerObj['ownerTeam']

        # adding points for ownerTeam
        owner_to_points_start[ownerTeam] += playerPoints

    print(owner_to_points_start)
    for owner_name, owner_points in owner_to_points_start.items():
        update_op = UpdateOne(
            {"ownerName": owner_name},
            {"$set": {"totalPoints": owner_points}}
        )
        update_ops.append(update_op)

    result = ownercollection.bulk_write(update_ops)

# Print the number of documents updated
    print("Number of documents updated:", result.matched_count)

    # updating time stamps
    timestamp_collection = db['timestamps']
    timestamp_collection.update_one(
        {}, {"$set": {"pointsUpdatedAt": get_formatted_timestamp()}})
    
    return json_util.dumps("Success")
   
   
@app.route('/updatestandings', methods=['POST'])
def updatestandings():
    ownersdata_cursor = ownercollection.find()

    
    owner_to_points ={}
    for owner in ownersdata_cursor:
        owner_to_points[owner["ownerName"]] = owner["totalPoints"]

    sorted_teams = sorted(owner_to_points.items(), key=lambda x: x[1], reverse=True)

    # create a new dictionary to store standings
    standings = {}
    rank = 1
    prev_points = None
    for idx, team in enumerate(sorted_teams):
        team_name = team[0]
        points = team[1]
        if prev_points is None or points < prev_points:
            standings[team_name] = rank
            rank +=  1
        else:
            standings[team_name] = rank-1
        prev_points = points

    stand_update_ownersdata_cursor = ownercollection.find()            

    for currowner in stand_update_ownersdata_cursor:
        currowner["standing"].append(standings[currowner["ownerName"]])
    
        filter_owner = {"_id": ObjectId(str(currowner["_id"]))}
        result_owner = ownercollection.update_one(filter_owner, {"$set": currowner})
         
    standing_collection = db['timestamps']
    standing_collection.update_one(
        {}, {"$set": {"rankingsUpdatedAt": get_formatted_timestamp()}})
    

    return json_util.dumps(result_owner.raw_result)
   
   
@app.route('/gettimestamps', methods=['GET'])
def gettimestamps():
    time_list = []
    timestamp_collection = db['timestamps']
    time_cursor = timestamp_collection.find()

    for time in time_cursor:
        time_list.append(time)
    return json.loads(json_util.dumps(time_list))

    
if __name__ == '__main__':
    app.run()
   
    
