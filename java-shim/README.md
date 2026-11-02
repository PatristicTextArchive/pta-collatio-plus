# pta-noscript-shim

CollateX 1.8 looks up a JavaScript engine (Nashorn) on start-up. Nashorn was removed in Java 15,
so CollateX fails with a NullPointerException on newer Java versions. This tiny jar registers a
"js" script engine that knows no functions, so CollateX falls back to its built-in tokenizer,
normaliser and comparator. Put it on the classpath next to the CollateX jar.

Build:

    javac --release 11 -d build src/ptashim/NoScriptEngineFactory.java
    cp -r META-INF build/ && (cd build && jar cf ../pta-noscript-shim.jar .)
