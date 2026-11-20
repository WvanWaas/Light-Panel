package app.lightpanel.launcher;

/** Pure values: no strings from the website are ever executed as shell commands. */
final class LedValues {
    static int channel(int value) {
        if (value < 0 || value > 255) throw new IllegalArgumentException("LED value must be 0–255");
        return value;
    }
    static int breatheBrightness(long elapsed, int maximum) {
        channel(maximum);
        double phase=(elapsed % 3200L)/3200.0;
        double wave=(1-Math.cos(2*Math.PI*phase))/2;
        return (int)Math.round(Math.min(8,maximum)+(maximum-Math.min(8,maximum))*wave);
    }
    static String frame(int brightness,int red,int green,int blue) {
        return "<"+channel(brightness)+","+channel(red)+","+channel(green)+","+channel(blue)+">";
    }
}
