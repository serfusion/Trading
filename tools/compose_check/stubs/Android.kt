package android.content
open class Context {
    open fun getSharedPreferences(name: String, mode: Int): SharedPreferences = TODO()
    open val applicationContext: Context get() = this
    open val assets: AssetManager get() = AssetManager()
    companion object { const val MODE_PRIVATE = 0 }
}
class AssetManager { fun open(name: String): java.io.InputStream = java.io.ByteArrayInputStream(ByteArray(0)) }
interface SharedPreferences {
    fun getString(k: String, d: String?): String?
    fun getBoolean(k: String, d: Boolean): Boolean
    fun getInt(k: String, d: Int): Int
    fun getLong(k: String, d: Long): Long
    fun getFloat(k: String, d: Float): Float
    fun getStringSet(k: String, d: Set<String>?): Set<String>?
    fun contains(k: String): Boolean
    val all: Map<String, *>
    fun edit(): Editor
    interface Editor {
        fun putString(k: String, v: String?): Editor
        fun putBoolean(k: String, v: Boolean): Editor
        fun putInt(k: String, v: Int): Editor
        fun putLong(k: String, v: Long): Editor
        fun putFloat(k: String, v: Float): Editor
        fun putStringSet(k: String, v: Set<String>?): Editor
        fun remove(k: String): Editor
        fun apply()
        fun commit(): Boolean
    }
}
