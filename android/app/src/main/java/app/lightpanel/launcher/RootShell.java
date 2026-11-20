package app.lightpanel.launcher;

import android.os.SystemClock;
import java.io.*;

/** One persistent root shell. Polling avoids API-26 Process.waitFor on Android 6. */
final class RootShell implements AutoCloseable {
    private Process process;
    private BufferedWriter writer;
    private BufferedReader reader;
    private long sequence;
    synchronized void execute(String command) throws IOException {
        try {
            if(process==null){
                process=new ProcessBuilder("su","-c","/system/bin/sh").redirectErrorStream(true).start();
                writer=new BufferedWriter(new OutputStreamWriter(process.getOutputStream()));
                reader=new BufferedReader(new InputStreamReader(process.getInputStream()));
            }
            String marker="FRAMEO_OK_"+(++sequence);
            writer.write(command+" && echo "+marker+" || echo FRAMEO_FAILED\n");writer.flush();
            long until=SystemClock.elapsedRealtime()+5000;
            StringBuilder line=new StringBuilder();
            while(SystemClock.elapsedRealtime()<until){
                if(Thread.currentThread().isInterrupted())throw new IOException("LED command interrupted");
                if(reader.ready()){
                    int character=reader.read();
                    if(character<0)throw new IOException("Root shell closed");
                    if(character=='\n'){
                        String value=line.toString().trim();line.setLength(0);
                        if(value.equals(marker))return;
                        if(value.equals("FRAMEO_FAILED"))throw new IOException("Root write refused");
                    }else if(line.length()<4096)line.append((char)character);
                }else{
                    try{process.exitValue();throw new IOException("Root access refused");}catch(IllegalThreadStateException running){}
                    try{Thread.sleep(10);}catch(InterruptedException e){Thread.currentThread().interrupt();throw new IOException("Interrupted",e);}
                }
            }
            throw new IOException("No root response within five seconds");
        }catch(IOException e){close();throw e;}
    }
    @Override public synchronized void close(){
        if(process!=null)process.destroy();
        try{if(writer!=null)writer.close();}catch(IOException ignored){}
        try{if(reader!=null)reader.close();}catch(IOException ignored){}
        process=null;writer=null;reader=null;
    }
}
