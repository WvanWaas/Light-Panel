package app.lightpanel.launcher;

import android.os.SystemClock;
import java.util.concurrent.*;

/** Native breathing needs neither HA, an ADB session nor a tablet shell script. */
final class LedController {
    interface Reply { void send(boolean success,String mode); }
    private final ScheduledExecutorService executor=Executors.newSingleThreadScheduledExecutor();
    private final RootShell shell=new RootShell();
    private ScheduledFuture<?> animation;
    private String mode="unknown",wantedMode="off";
    private int wantedBrightness,wantedRed,wantedGreen,wantedBlue;
    private boolean screenEnabled=true;
    private boolean prepared;
    private volatile boolean closed;
    private long started;
    private int maximum;
    private static final String STOP_LEGACY="if [ -f /data/local/tmp/frameo_breathe.pid ]; then "
        +"read old < /data/local/tmp/frameo_breathe.pid; case \"$old\" in ''|*[!0-9]*) ;; *) "
        +"case \"$(cat /proc/$old/cmdline 2>/dev/null)\" in *frameo_breathe.sh*) kill \"$old\" 2>/dev/null ;; esac ;; esac; "
        +"rm -f /data/local/tmp/frameo_breathe.pid; fi; true";
    void set(String wanted,int brightness,int red,int green,int blue,Reply reply){
        LedValues.frame(brightness,red,green,blue);
        if(!wanted.equals("color")&&!wanted.equals("off")&&!wanted.equals("breathe"))throw new IllegalArgumentException("Unsupported LED mode");
        if(closed)return;
        executor.execute(()->{
            wantedMode=wanted;wantedBrightness=brightness;wantedRed=red;wantedGreen=green;wantedBlue=blue;
            applyCurrent(reply);
        });
    }
    void setScreenEnabled(boolean enabled,Reply reply){
        if(closed)return;
        executor.execute(()->{screenEnabled=enabled;applyCurrent(reply);});
    }
    private void applyCurrent(Reply reply){
        stopAnimation();
        try{
            if(!prepared){shell.execute(STOP_LEGACY);prepared=true;}
            mode=screenEnabled?wantedMode:"off";
            if(mode.equals("breathe")){
                maximum=wantedBrightness;started=SystemClock.elapsedRealtime();
                write(LedValues.breatheBrightness(0,maximum),255,0,0);
                animation=executor.scheduleWithFixedDelay(()->{
                    try{write(LedValues.breatheBrightness(SystemClock.elapsedRealtime()-started,maximum),255,0,0);}
                    catch(Exception error){stopAnimation();mode="error";prepared=false;reply.send(false,mode);}
                },100,100,TimeUnit.MILLISECONDS);
            }else if(mode.equals("off"))write(0,0,0,0);
            else write(wantedBrightness,wantedRed,wantedGreen,wantedBlue);
            reply.send(true,mode);
        }catch(Exception error){mode="error";prepared=false;reply.send(false,mode);}
    }
    private void write(int brightness,int red,int green,int blue) throws Exception {
        shell.execute("printf '%s\\n' '"+LedValues.frame(brightness,red,green,blue)+"' > /sdcard/frameo_light.txt");
    }
    private void stopAnimation(){if(animation!=null){animation.cancel(false);animation=null;}}
    void close(){closed=true;executor.shutdownNow();shell.close();}
}
