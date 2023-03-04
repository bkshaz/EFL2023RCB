from flask import Flask,make_response,request
from pymongo import MongoClient
import random
from bson import json_util,ObjectId
import json
from flask_cors import CORS
import urllib.parse

app = Flask(__name__)
CORS(app)
client = MongoClient("mongodb+srv://efladmin:god_is_watching@cluster0.eezohvz.mongodb.net/?retryWrites=true&w=majority")

db=client["efl2023"]

collections = db["eflCricket"]

ownercollection = db["eflCricketOwners"]

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
            "standing":[]
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
    
if __name__ == '__main__':
    app.run()
    
