#include "WarGraphicsBootstrap.h"
#include "Modules/ModuleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void WarGraphicsBootstrap::PrepareConfig(FConfigCacheIni& Config, const FString& Ini, bool Safe)
{
    const TCHAR* Section = TEXT("/Script/AegisWar.WarGraphicsSettings");
    auto* File = Config.FindConfigFile(Ini);
    if (!File) return;
    // Copy only the graphics class section, leaving shared bindings/audio/UI untouched.
    if (!File->FindSection(Section))
    {
        if (const auto* Legacy = File->FindSection(TEXT("/Script/Engine.GameUserSettings")))
            File->Add(Section, *Legacy);
        else
        {
            Config.SetInt(Section, TEXT("FullscreenMode"), 1, Ini);
            Config.SetInt(Section, TEXT("ResolutionSizeX"), 0, Ini);
            Config.SetInt(Section, TEXT("ResolutionSizeY"), 0, Ini);
            Config.SetBool(Section, TEXT("bUseDesktopResolution"), true, Ini);
            Config.SetFloat(Section, TEXT("FrameRateLimit"), 60, Ini);
            Config.SetBool(Section, TEXT("bUseVSync"), true, Ini);
            for (const TCHAR* Group : {TEXT("ViewDistance"), TEXT("AntiAliasing"), TEXT("Shadow"), TEXT("GlobalIllumination"), TEXT("Reflection"), TEXT("PostProcess"), TEXT("Texture"), TEXT("Effects"), TEXT("Foliage"), TEXT("Shading"), TEXT("Landscape")})
                Config.SetInt(TEXT("ScalabilityGroups"), *(FString(TEXT("sg.")) + Group + TEXT("Quality")), 0, Ini);
            Config.SetFloat(TEXT("ScalabilityGroups"), TEXT("sg.ResolutionQuality"), 75, Ini);
        }
    }
    // This is Unreal 5.8's user-settings version. Do not let the base validator erase
    // unrelated sections when migrating an older or partially corrupt preferences file.
    Config.SetInt(Section, TEXT("Version"), 5, Ini);
    int32 Mode = 1, Width = 0, Height = 0;
    Config.GetInt(Section, TEXT("FullscreenMode"), Mode, Ini);
    Config.GetInt(Section, TEXT("ResolutionSizeX"), Width, Ini);
    Config.GetInt(Section, TEXT("ResolutionSizeY"), Height, Ini);

    if (Safe || Mode < 0 || Mode > 2 || Width < 0 || Height < 0 || Width > 32768 || Height > 32768)
    {
        Config.SetInt(Section, TEXT("FullscreenMode"), 2, Ini);
        Config.SetInt(Section, TEXT("ResolutionSizeX"), 1280, Ini);
        Config.SetInt(Section, TEXT("ResolutionSizeY"), 720, Ini);
        Config.SetBool(Section, TEXT("bUseDesktopResolution"), false, Ini);
    }
    if (Safe)
    {
        Config.SetFloat(Section, TEXT("FrameRateLimit"), 60, Ini);
        Config.SetBool(Section, TEXT("bUseVSync"), true, Ini);
        for (const TCHAR* Group : {TEXT("ViewDistance"), TEXT("AntiAliasing"), TEXT("Shadow"), TEXT("GlobalIllumination"), TEXT("Reflection"), TEXT("PostProcess"), TEXT("Texture"), TEXT("Effects"), TEXT("Foliage"), TEXT("Shading"), TEXT("Landscape")})
            Config.SetInt(TEXT("ScalabilityGroups"), *(FString(TEXT("sg.")) + Group + TEXT("Quality")), 0, Ini);
        Config.SetFloat(TEXT("ScalabilityGroups"), TEXT("sg.ResolutionQuality"), 75, Ini);
    }
}

/** No Engine/UObject dependency: runs before Unreal preloads the initial window mode. */
class FWarGraphicsBootstrap : public IModuleInterface
{
public:
    virtual void StartupModule() override
    {
        if (IsRunningDedicatedServer() || IsRunningCommandlet()) return;
        FConfigCacheIni::LoadGlobalIniFile(GGameUserSettingsIni, TEXT("GameUserSettings"));
        const bool Safe = FParse::Param(FCommandLine::Get(), TEXT("WarSafeGraphics"));
        WarGraphicsBootstrap::PrepareConfig(*GConfig, GGameUserSettingsIni, Safe);
        if (Safe)
        {
            const FString Original = FCommandLine::Get();
            FCommandLine::Set(*(FString(TEXT("-windowed -Res=1280x720w -ResX=1280 -ResY=720 ")) + Original));
        }
    }
};
IMPLEMENT_MODULE(FWarGraphicsBootstrap, WarGraphicsBootstrap)