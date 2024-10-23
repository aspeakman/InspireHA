#!/bin/bash
USERNAME='REPLACE_ME'
PASSWORD='REPLACE_ME'
APIKEY='REPLACE_ME'
URL="https://www.inspirehomeautomation.co.uk/client/api1_4/api.php?"
MYVARS="action=connect&apikey=$APIKEY&username=$USERNAME&password=$PASSWORD"
echo
echo "POST $URL"
echo "DATA $MYVARS"
RESULT=$(curl -s -d "$MYVARS" $URL)
echo CONNECT RESULT
echo $RESULT
echo
TEMP=${RESULT#*<key>}
KEY=${TEMP%</key>*}
MYVARS="action=get_devices&apikey=$APIKEY&key=$KEY"
echo "GET $URL$MYVARS"
RESULT=$(curl -s "$URL$MYVARS")
echo GET_DEVICES RESULT
echo $RESULT