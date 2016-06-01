database = {
    "hostname": "",
    "portNo": "27017",
    "database": "",
    "collection": "",
    "collection_stats": "",
    "replicaSet": "",
    "username": "",
    "password": ""
}

docker = {
    "api": "",
    "network": "swarm_network"
}

container = {
    "api_port": "80",
    "api_path": "/getconfig",
    "default_message": '{"name":"Gordon","twitter":"@docker","location":"San Francisco, CA, USA",' \
                       '"repo":["example/examplevotingapp_voting-app",' \
                       '"example/examplevotingapp_result-app"],"vote":"Cat"}'
}
twitter = {
    "tweet_message": "Just completed the #dockerbday training!"
                     " Built, shipped & ran my first app using "
                     "@docker: docker.party #learndocker #docker",
    "tweet_link": "https://twitter.com/intent/tweet?text="
}

misc = {
    "allowed_votes": ["Applescript", "Assembly", "Angular", "Lisp", "Actionscript", "Bash", "Basic",
                      "Cuda", "Clojure", "Coffescript", "C", "C++", "C#", "Caml", "Dart", "Ecmascript",
                      "Erlang", "Go", "Golang", "Groovy", "Haskell", "Java", "Javascript", "Jython", "Kotlin",
                      "Logo", "Lua", "Machine Code", "Matlab", "Node.Js", "Objective-C", "Ocaml", "Pascal",
                      "Perl", "Php", "Python", "Ruby", "Ruby On Rails", "Scala", "Swift", "Sql", "Tcl",
                      "Visual Basic", "Vba", "Asp.Net", "Visual Basic.Net", ".Net", "Html", "Css", "Xml",
                      "Xquery", "Xslt"]
}

# consul = {
#     "host": "consul",
#     "port": "8500",
#     "key": "docker/swarm/leader"
# }
