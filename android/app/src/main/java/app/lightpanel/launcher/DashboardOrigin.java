package app.lightpanel.launcher;
import java.net.URI;
final class DashboardOrigin {
    private final URI origin;
    DashboardOrigin(String dashboard){origin=URI.create(dashboard);}
    boolean allows(String url){
        try{URI candidate=URI.create(url);return candidate.getUserInfo()==null&&origin.getScheme().equalsIgnoreCase(candidate.getScheme())&&origin.getHost().equalsIgnoreCase(candidate.getHost())&&port(origin)==port(candidate);}catch(Exception e){return false;}
    }
    private static int port(URI uri){return uri.getPort()!=-1?uri.getPort():"https".equalsIgnoreCase(uri.getScheme())?443:80;}
    String value(){return origin.getScheme()+"://"+origin.getHost()+":"+port(origin);}
}
