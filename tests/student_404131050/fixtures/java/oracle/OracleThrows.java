package oracle;

class FirstException extends Exception {
}

class SecondException extends Exception {
}

class OracleThrows {

    OracleThrows() throws FirstException, SecondException {
    }

    void execute() throws FirstException, SecondException {
    }
}

interface OracleContract {

    void run() throws FirstException, SecondException;
}