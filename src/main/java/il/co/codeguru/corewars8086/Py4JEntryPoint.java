package il.co.codeguru.corewars8086;

import py4j.GatewayServer;

public class Py4JEntryPoint {
    public static void main(String[] args) {
        GatewayServer server = new GatewayServer(null);
        server.start();
        System.out.println("Py4J Gateway Server Started");
    }
}

