package app.lightpanel.launcher;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ResolveInfo;
import android.util.Log;

/** Boot fallback for the supported Android 6 frame; respects the chosen HOME app. */
public final class BootReceiver extends BroadcastReceiver {
    static final String EXTRA_FROM_BOOT = "app.lightpanel.launcher.FROM_BOOT";
    @Override public void onReceive(Context context, Intent received) {
        if (received == null || !Intent.ACTION_BOOT_COMPLETED.equals(received.getAction())) return;
        Intent home = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME);
        ResolveInfo chosen = context.getPackageManager().resolveActivity(home, 0);
        if (chosen == null || chosen.activityInfo == null ||
                !context.getPackageName().equals(chosen.activityInfo.packageName)) {
            Log.i("LightPanelBoot", "Choose Light Panel as the default HOME app to start on boot.");
            return;
        }
        Intent launch = new Intent(context, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP)
                .putExtra(EXTRA_FROM_BOOT, true);
        try { context.startActivity(launch); }
        catch (RuntimeException error) { Log.e("LightPanelBoot", "Could not open dashboard after boot", error); }
    }
}
