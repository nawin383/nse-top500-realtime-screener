# kotlinx.serialization generates a synthetic $serializer companion for each
# @Serializable class that R8 can't see from the static call graph (it's only
# reached via reflection at runtime) -- keep our model + its serializer or
# backup import/export silently breaks under minification.
-keepattributes *Annotation*, InnerClasses
-keep,includedescriptorclasses class com.puretext.launcher.data.**$$serializer { *; }
-keepclassmembers class com.puretext.launcher.data.** {
    *** Companion;
}
-keepclasseswithmembers class com.puretext.launcher.data.** {
    kotlinx.serialization.KSerializer serializer(...);
}
