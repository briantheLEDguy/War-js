#pragma once
#include "CoreMinimal.h"

enum class EWarCombatUiPart : uint8 { Reticle, OverheadHealth, Damage, Critical, Healing, Panel, Name, Health, HealthText, Cast, HitMarker, Feed };
struct FWarCombatUiStyle
{
    bool Visible = true, Shadow = true;
    float X = 0, Y = 0, Width = 84, Height = 10, Scale = 1, Font = 16;
    float Padding = 8, Thickness = 3, Opacity = 1, Lifetime = 1, Rise = 64, Burst = 5;
    FLinearColor Colors[6] = {FLinearColor::White, FLinearColor(.03f,.025f,.02f,.94f), FLinearColor::Black,
        FLinearColor(1,.65f,.15f), FLinearColor(.4f,1,.5f), FLinearColor(.65f,.8f,1)};
};
struct FWarCombatUiField
{
    const TCHAR* Name;
    float FWarCombatUiStyle::* Member;
    float Min, Max;
};
struct AEGISWAR_API FWarCombatUiSettings
{
    static constexpr int32 Count = 22;
    FWarCombatUiStyle Styles[Count];
    FWarCombatUiSettings();
    void Load(const FString& Filename);
    void Save(const FString& Filename) const;
    void Set(int32 Id, const FWarCombatUiStyle& Style);
    void Reset(int32 Id);
    void CopySide(int32 Id);
};
namespace WarCombatUi
{
    AEGISWAR_API int32 Id(EWarCombatUiPart Part, bool Enemy = false);
    AEGISWAR_API EWarCombatUiPart Part(int32 Id);
    AEGISWAR_API FString Label(int32 Id);
    AEGISWAR_API FWarCombatUiStyle Defaults(int32 Id);
    AEGISWAR_API TArray<FWarCombatUiField> Fields(int32 Id);
    AEGISWAR_API FString ColorLabel(int32 Id, int32 Color);
    AEGISWAR_API bool ScreenRelative(int32 Id);
    AEGISWAR_API FWarCombatUiStyle Sanitize(int32 Id, FWarCombatUiStyle Style);
    AEGISWAR_API void Move(FWarCombatUiSettings& Settings, int32 Id, FVector2D Delta, FVector2D View, float HudScale);
}
