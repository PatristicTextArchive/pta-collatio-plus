package ptashim;

import javax.script.*;
import java.io.Reader;
import java.util.List;

/**
 * Minimal stand-in for the Nashorn JavaScript engine that CollateX 1.8 looks up on start-up.
 * CollateX only needs an engine to evaluate an (empty) plug-in script and to probe for the
 * functions tokenize/normalize/compare. This engine knows no functions, so CollateX falls back
 * to its built-in behaviour. That lifts the "Java < 15" restriction.
 */
public class NoScriptEngineFactory implements ScriptEngineFactory {
    public String getEngineName() { return "pta-noscript"; }
    public String getEngineVersion() { return "1.0"; }
    public List<String> getExtensions() { return List.of("js"); }
    public List<String> getMimeTypes() { return List.of("application/javascript"); }
    public List<String> getNames() { return List.of("pta-noscript"); }
    public String getLanguageName() { return "none"; }
    public String getLanguageVersion() { return "0"; }
    public Object getParameter(String key) { return null; }
    public String getMethodCallSyntax(String obj, String m, String... args) { return ""; }
    public String getOutputStatement(String toDisplay) { return ""; }
    public String getProgram(String... statements) { return ""; }
    public ScriptEngine getScriptEngine() { return new Engine(this); }

    static class Engine extends AbstractScriptEngine implements Compilable, Invocable {
        private final ScriptEngineFactory factory;
        Engine(ScriptEngineFactory f) { this.factory = f; }
        public Object eval(String script, ScriptContext ctx) { return null; }
        public Object eval(Reader reader, ScriptContext ctx) { return null; }
        public Bindings createBindings() { return new SimpleBindings(); }
        public ScriptEngineFactory getFactory() { return factory; }
        public CompiledScript compile(String script) { return compiled(); }
        public CompiledScript compile(Reader script) { return compiled(); }
        private CompiledScript compiled() {
            final Engine self = this;
            return new CompiledScript() {
                public Object eval(ScriptContext ctx) { return null; }
                public ScriptEngine getEngine() { return self; }
            };
        }
        public Object invokeMethod(Object thiz, String name, Object... args) throws NoSuchMethodException { throw new NoSuchMethodException(name); }
        public Object invokeFunction(String name, Object... args) throws NoSuchMethodException { throw new NoSuchMethodException(name); }
        public <T> T getInterface(Class<T> clasz) { return null; }
        public <T> T getInterface(Object thiz, Class<T> clasz) { return null; }
    }
}
