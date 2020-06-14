import socket
import select
import sys
import time
import re

# Code executed to listen to port 4000 on the localhost (127.0.0.1)
# Listens to commands in format /?find=NAME, /?add=NAME:AMOUNT, /?take=NAME:AMOUNT
# There is a linked html file that sorts our interaction
# By Josh Collier, June 2020

# -------------------------------------------------- Initialising Variables ---------------------------------------------------
# Setting some global constants
fileName = "parts.txt"
maxReadSize = 1024
tcpPort = 4000

httpHeaders = "HTTP/1.1 200 OK\nContent-Type: text/html\nConnection: Closed\n\n"
htmlHeader = "<html>\n<body>\n<h1>\n"
htmlTail = "\n</h1>\n</body>\n</html>\n"

# Initialise empty 8x8 array
parts = []
for i in range(8):
    parts.append([])
    for j in range(8):
        parts[i].append([])
        parts[i][j].append("N/A")
        parts[i][j].append(0)


# ---------------------------------------------------- Dealing with Funcs -----------------------------------------------------
def buildParts():
    # Build parts array
    partsFile = open(fileName, "r")
    partsFileLines = partsFile.readlines()
    for i in range(len(partsFileLines)):
        line = partsFileLines[i].strip()
        lineComponents = line.split(",")
        for j in range(len(lineComponents)):
            itemComponents = lineComponents[j].split(":")
            parts[i][j][0] = itemComponents[0]
            parts[i][j][1] = int(itemComponents[1])
    partsFile.close()

def uploadChanges():
    partsFile = open(fileName, "w")
    for i in range(len(parts)):
        partsLine = ""
        for j in range(len(parts[i])):
            partsLine += parts[i][j][0] + ":" + str(parts[i][j][1]) + ","
        partsLine = partsLine[0:-1]
        partsFile.write(partsLine+"\n")
    partsFile.close()

def sendAndClose(message, sock):
    sock.send((httpHeaders + htmlHeader + message + htmlTail).encode('utf-8'))
    sock.close()


# ------------------------------------------------------- TCP Listening -------------------------------------------------------
# Create TCP socket
tcpSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpSock.bind(('localhost', tcpPort))
tcpSock.listen(1)
listening = True

buildParts()

# On the webpage we will generate it from the partsFile, which will allow you to take,
# add or find parts with simple buttons in a html page 
while(listening):
    clientSock, address = tcpSock.accept()
    
    data = clientSock.recv(maxReadSize)
    dataStr = data.decode('utf-8')
    
    if data:
        print("Client Accepted")
        print("We just recieved:", data)
        print("Current Parts:")
        print(parts)
        # --------------------------------------------- We are looking for a part ---------------------------------------------
        if ("GET /?find=" in dataStr):
            partLookingFor = re.search(r'(?<=\?find=)\w+', dataStr).group(0)
            print("Finding", partLookingFor)

            replyX, replyY = "", ""
            found = False
            for i in range(8):
                for j in range(8):
                    if (parts[i][j][0] == partLookingFor):
                        replyX, replyY = str(j), str(i)
                        print("Look in row " + replyX + ", column" + replyY)
                        found = True

            # Reply and close socket
            if (found):
                replyMessage = "Look in row " + replyX + ", column" + replyY
            else:
                replyMessage = "Find failed."
            sendAndClose(replyMessage, clientSock)

        # ----------------------------------------------- We are adding a part/s ----------------------------------------------
        if ("GET /?add=" in dataStr):
            add = re.search(r'(?<=\?add=)\w+:\w+', dataStr).group(0)
            add = add.split(":")
            addPart = add[0]
            addNo = int(add[1])
            print("Adding", str(addNo), addPart)

            partsNow = 0

            # We will check if the part is in the list, if so we will add to its total, if
            # not we will add it to the next available slot and give it the amount provided
            weveAdded = False
            for i in range(8):
                for j in range(8):
                    if (parts[i][j][0] == addPart):
                        parts[i][j][1] += addNo
                        partsNow = parts[i][j][1]
                        weveAdded=True
                        break
                    elif (parts[i][j][0] == "N/A"):
                        parts[i][j][0] = addPart
                        parts[i][j][1] += addNo
                        partsNow = parts[i][j][1]
                        weveAdded=True
                        break
                if (weveAdded):
                    break
                
            uploadChanges()
            # Reply and close socket (and text pedantics)
            addS = ""
            if (partsNow == 1):
                addS = "s"
            replyMessage = ""
            if (weveAdded):
                replyMessage = "You now have " + str(partsNow) + " " + addPart + addS + "."
            else:
                replyMessage = "Addition failed."
            sendAndClose(replyMessage, clientSock)
            
        # ---------------------------------------------- We are removing a part/s ---------------------------------------------
        if ("GET /?take=" in dataStr):
            take = re.search(r'(?<=\?take=)\w+:\w+', dataStr).group(0)
            take = take.split(":")
            takePart = take[0]
            takeNo = int(take[1])
            print("Removing", str(takeNo), takePart)

            partsNow = 0
            
            # We will check if we have any of this part, and we will remove this amout
            # if we have that many
            weveRemoved = False
            weCantRemove = False
            weDontHave = True
            for i in range(8):
                for j in range(8):
                    if (parts[i][j][0] == takePart):
                        if (parts[i][j][1] >= takeNo):
                            parts[i][j][1] -= takeNo
                            partsNow = parts[i][j][1]
                            weveRemoved = True
                            break
                        elif (parts[i][j][1] < takeNo):
                            partsNow = parts[i][j][1]
                            weCantRemove = True
                            break
                if (weveRemoved or weCantRemove):
                    weDontHave = False
                    break

            uploadChanges()
            # Reply and close socket (and text pedantics)
            replyMessage = ""
            addS = ""
            if (partsNow == 1):
                addS = "s"
            if (weveRemoved):
                replyMessage = "You now have " + str(partsNow) + " " + takePart + addS + "."
            elif (weDontHave):
                anyS = ["a", ""]
                if (takeNo == 1):
                    anyS = ["any", "s"]
                replyMessage + "You dont have " + anyS[0] + " " + takePart + anyS[1]
            elif (weCantRemove):
                replyMessage = "You dont have enough, you only have " + str(partsNow) + " " + takePart + addS + "."

            sendAndClose(replyMessage, clientSock)
        
        # ---------------------------------------------- We are swapping a part/s ---------------------------------------------
        if ("GET /?swap=" in dataStr):
            swap = re.search(r'(?<=\?swap=)\w+,\w+', dataStr).group(0)
            swap = swap.split(",")

            foundOne = False
            foundTwo = False
            done = False
            otherPart = []
            for i in range(8):
                for j in range(8):
                    if (parts[i][j][0] == swap[0]):
                        if (foundTwo):
                            otherParti = otherPart[0]
                            otherPartj = otherPart[1]
                            buf = parts[otherParti][otherPartj]
                            parts[otherParti][otherPartj] = parts[i][j]
                            parts[i][j] = buf
                            done = True
                        else:
                            # We have found 1, now we have to find the other
                            foundOne = True
                            otherPart = [i,j]
                    elif (parts[i][j][0] == swap[1]):
                        if (foundOne):
                            otherParti = otherPart[0]
                            otherPartj = otherPart[1]
                            buf = parts[otherParti][otherPartj]
                            parts[otherParti][otherPartj] = parts[i][j]
                            parts[i][j] = buf
                            done = True
                        else:
                            # We have found 1, now we have to find the other
                            foundTwo = True
                            otherPart = [i,j]
                if (done):
                    break
            
            uploadChanges()
            # Reply and close socket (and text pedantics)
            replyMessage = ""
            if (done):
                replyMessage = "You have swapped " + swap[0] + " with " + swap[1] + "."
            else:
                replyMessage = "Swap failed."
            sendAndClose(replyMessage, clientSock) 

    else:
        print("Closing client socket")
        clientSock.close()