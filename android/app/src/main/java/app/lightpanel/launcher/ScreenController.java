package app.lightpanel.launcher;

import android.content.Context;
import android.content.SharedPreferences;
import java.io.*;
import java.util.concurrent.*;

/** Only controls this frame's backlight; Android and the network stay awake. */
final class ScreenController {
    private static final String PATH="/sys/class/backlight/rk28_bl/brightness";
    interface Reply { void send(boolean ok,boolean on); }
    private final ExecutorService executor=Executors.newSingleThreadExecutor();
    private final RootShell shell=new RootShell();
    private final SharedPreferences prefs;
    private volatile boolean on=true;
    ScreenController(Context context){prefs=context.getSharedPreferences("screen",Context.MODE_PRIVATE);try{on=read()>0;}catch(Exception ignored){}}
    boolean available(){return new File(PATH).exists();}
    boolean isOn(){return on;}
    private int read() throws IOException {try(BufferedReader r=new BufferedReader(new FileReader(PATH))){return Integer.parseInt(r.readLine().trim());}}
    void set(boolean wanted,Reply reply){
        executor.execute(()->{
            try{
                int current=read();
                if(!wanted&&current>0)prefs.edit().putInt("brightness",current).apply();
                int value=wanted?Math.max(1,Math.min(255,prefs.getInt("brightness",255))):0;
                shell.execute("echo "+value+" > "+PATH+" && test \"$(cat "+PATH+")\" = "+value);
                on=read()>0;reply.send(on==wanted,on);
            }catch(Exception error){reply.send(false,on);}
        });
    }
    void close(){executor.execute(shell::close);executor.shutdown();}
}
