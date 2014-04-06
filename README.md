sshgo
=====

script for managing ssh hosts list

##screenshot
![screenshot](https://raw.github.com/emptyhua/sshgo/master/screenshot.png)

##~/.ssh_hosts example
    #add `-` before the line can close node 
    -Home
        root@192.168.1.106
    Work
        root@comp1 -p 9999
        root@comp2 -p 9999
        root@comp3 -p 9999
    VHost
        VMWare
            test@vm1
            test@vm2
            test@vm3
            test@vm4
        -VirtualBox:
            test@vbox1
            test@vbox2
            test@vbox3
            test@vbox4
    MacOS
        hi@mymac

##Keyboard shortcuts
* exit: q
* scroll up: k
* scroll down: j
* page up: u
* page down: d
* select host: space
* search mode: /
* exit from search result: q
* expand tree node: o
* collapse tree node: c
* expand all nodes: O
* collapse all nodes: C
