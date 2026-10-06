#include "WarCombatUiSettings.h"
#include "Misc/ConfigCacheIni.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace { constexpr const TCHAR* Section = TEXT("AegisWar.CombatUi.v1"); }
int32 WarCombatUi::Id(EWarCombatUiPart P, bool Enemy) { return P >= EWarCombatUiPart::HitMarker ? 20 + int32(P) - 10 : int32(P) + (Enemy ? 10 : 0); }
EWarCombatUiPart WarCombatUi::Part(int32 I) { return static_cast<EWarCombatUiPart>(I >= 20 ? I - 10 : I % 10); }
bool WarCombatUi::ScreenRelative(int32 I) { const auto P = Part(I); return P == EWarCombatUiPart::Panel || I >= 20; }
FString WarCombatUi::Label(int32 I)
{
    const TCHAR* Names[] = {TEXT("Target reticle"),TEXT("Overhead health"),TEXT("Normal damage"),TEXT("Critical damage"),TEXT("Healing"),TEXT("Target panel"),TEXT("Target name"),TEXT("Target health bar"),TEXT("Target health text"),TEXT("Target cast bar"),TEXT("Hit marker"),TEXT("Combat messages")};
    return (I < 20 ? FString(I < 10 ? TEXT("Friendly / ") : TEXT("Enemy / ")) : FString()) + Names[int32(Part(I))];
}
FWarCombatUiStyle WarCombatUi::Defaults(int32 I)
{
    FWarCombatUiStyle S; const auto P = Part(I);
    S.Colors[0] = I < 10 ? FLinearColor(.08f,.45f,1) : FLinearColor(1,.08f,.06f);
    if (P == EWarCombatUiPart::Reticle) S.Colors[2]=FLinearColor(0,0,0,.9f);
    if (P == EWarCombatUiPart::OverheadHealth) { S.Thickness = 1; S.Colors[1] = FLinearColor(.11f,.12f,.14f,.95f); }
    if (P >= EWarCombatUiPart::Damage && P <= EWarCombatUiPart::Healing)
    {
        S.Font = P == EWarCombatUiPart::Critical ? 20.7f : 18; S.Y = -12;
        S.Colors[0] = P == EWarCombatUiPart::Healing ? FLinearColor(.3f,1,.4f)
            : P == EWarCombatUiPart::Critical ? FLinearColor(1,.6f,.12f) : FLinearColor(1,.94f,.75f);
    }
    if (P == EWarCombatUiPart::Panel) { S.X=.5f; S.Y=.012f; S.Width=380; S.Height=108; S.Thickness=0; }
    if (P == EWarCombatUiPart::Name) { S.X=10; S.Y=5; S.Width=360; S.Colors[0]=FLinearColor(1,.85f,.55f); }
    if (P == EWarCombatUiPart::Health) { S.X=10; S.Y=33; S.Width=360; S.Height=20; S.Thickness=0; S.Colors[1]=FLinearColor(.12f,.1f,.08f); }
    if (P == EWarCombatUiPart::HealthText) { S.X=15; S.Y=34; S.Width=350; S.Font=13; S.Colors[0]=FLinearColor::White; }
    if (P == EWarCombatUiPart::Cast) { S.X=10; S.Y=60; S.Width=360; S.Height=9; S.Font=13; S.Thickness=0; S.Colors[0]=FLinearColor(.85f,.6f,.15f); S.Colors[1]=FLinearColor(.18f,.14f,.06f); }
    if (P == EWarCombatUiPart::HitMarker) { S.X=.5f; S.Y=.5f; S.Width=20; S.Height=20; S.Thickness=2; S.Colors[0]=FLinearColor(1,.85f,.25f); S.Colors[3]=FLinearColor(1,.55f,.25f); }
    if (P == EWarCombatUiPart::Feed) { S.X=1; S.Y=.52f; S.Width=350; S.Font=13; S.Colors[0]=FLinearColor::White; S.Colors[1]=FLinearColor(.018f,.014f,.01f,.9f); S.Colors[2]=FLinearColor(1,.8f,.2f); }
    return S;
}
TArray<FWarCombatUiField> WarCombatUi::Fields(int32 I)
{
    const auto P=Part(I); const bool Screen=ScreenRelative(I);
    TArray<FWarCombatUiField> F={{TEXT("X"),&FWarCombatUiStyle::X,Screen?0.f:-300.f,Screen?1.f:300.f},
        {TEXT("Y"),&FWarCombatUiStyle::Y,Screen?0.f:-300.f,Screen?1.f:300.f},
        {TEXT("Scale"),&FWarCombatUiStyle::Scale,.5f,2.f},{TEXT("Opacity"),&FWarCombatUiStyle::Opacity,0,1}};
    const bool Number=P>=EWarCombatUiPart::Damage && P<=EWarCombatUiPart::Healing;
    if (Number || P==EWarCombatUiPart::Name || P==EWarCombatUiPart::HealthText || P==EWarCombatUiPart::Cast || P==EWarCombatUiPart::Feed)
        F.Add({TEXT("Text size"),&FWarCombatUiStyle::Font,8,36});
    if (!Number && P!=EWarCombatUiPart::Reticle)
        F.Add({TEXT("Width"),&FWarCombatUiStyle::Width,16,700});
    if (P==EWarCombatUiPart::OverheadHealth || P==EWarCombatUiPart::Health || P==EWarCombatUiPart::Cast || P==EWarCombatUiPart::Panel || P==EWarCombatUiPart::HitMarker)
        F.Add({TEXT("Height"),&FWarCombatUiStyle::Height,4,P==EWarCombatUiPart::Panel?240.f:40.f});
    if (P==EWarCombatUiPart::Reticle) F.Add({TEXT("Padding"),&FWarCombatUiStyle::Padding,0,64});
    if (P==EWarCombatUiPart::Reticle || P==EWarCombatUiPart::OverheadHealth || P==EWarCombatUiPart::Health || P==EWarCombatUiPart::Cast || P==EWarCombatUiPart::Panel || P==EWarCombatUiPart::HitMarker)
        F.Add({TEXT("Line / border"),&FWarCombatUiStyle::Thickness,0,8});
    if (Number)
    {
        F.Add({TEXT("Lifetime (s)"),&FWarCombatUiStyle::Lifetime,.25f,2});
        F.Add({TEXT("Rise (px)"),&FWarCombatUiStyle::Rise,16,128});
        F.Add({TEXT("Burst speed"),&FWarCombatUiStyle::Burst,1,8});
    }
    return F;
}
FString WarCombatUi::ColorLabel(int32 I, int32 C)
{
    if (Part(I)==EWarCombatUiPart::Feed) { const TCHAR* N[]={TEXT("Damage"),TEXT("Background"),TEXT("Interrupt"),TEXT("Critical"),TEXT("Healing"),TEXT("Guarded")}; return N[C]; }
    if (Part(I)==EWarCombatUiPart::HitMarker) return C==0?TEXT("Normal"):C==3?TEXT("Critical"):TEXT("");
    if (C==0) return Part(I)==EWarCombatUiPart::Panel?TEXT(""):TEXT("Foreground / fill");
    if (C==1 && (Part(I)==EWarCombatUiPart::Panel || Part(I)==EWarCombatUiPart::OverheadHealth || Part(I)==EWarCombatUiPart::Health || Part(I)==EWarCombatUiPart::Cast)) return TEXT("Background");
    if (C==2) return TEXT("Border / shadow");
    return TEXT("");
}
FWarCombatUiStyle WarCombatUi::Sanitize(int32 I, FWarCombatUiStyle S)
{
    const auto D=Defaults(I);
    for (const auto& F:Fields(I)) { float& V=S.*(F.Member); if (!FMath::IsFinite(V) || V<F.Min || V>F.Max) V=D.*(F.Member); }
    for (int32 C=0;C<6;++C)
        if (!FMath::IsFinite(S.Colors[C].R) || !FMath::IsFinite(S.Colors[C].G) || !FMath::IsFinite(S.Colors[C].B) || !FMath::IsFinite(S.Colors[C].A)
            || S.Colors[C].R<0 || S.Colors[C].R>1 || S.Colors[C].G<0 || S.Colors[C].G>1 || S.Colors[C].B<0 || S.Colors[C].B>1 || S.Colors[C].A<0 || S.Colors[C].A>1) S.Colors[C]=D.Colors[C];
    return S;
}
FWarCombatUiSettings::FWarCombatUiSettings() { for (int32 I=0;I<Count;++I) Styles[I]=WarCombatUi::Defaults(I); }
void FWarCombatUiSettings::Set(int32 I,const FWarCombatUiStyle& S) { if (I>=0 && I<Count) Styles[I]=WarCombatUi::Sanitize(I,S); }
void FWarCombatUiSettings::Reset(int32 I) { if (I>=0 && I<Count) Styles[I]=WarCombatUi::Defaults(I); }
void FWarCombatUiSettings::CopySide(int32 I) { if (I>=0 && I<20) Set((I+10)%20,Styles[I]); }
void WarCombatUi::Move(FWarCombatUiSettings& Settings,int32 I,FVector2D Delta,FVector2D View,float HudScale)
{
    if (I<0 || I>=FWarCombatUiSettings::Count || Delta.ContainsNaN() || View.X<=0 || View.Y<=0 || HudScale<=0) return;
    auto S=Settings.Styles[I];
    float Factor=HudScale;
    if (I<20 && int32(Part(I))>=6) Factor*=Settings.Styles[Id(EWarCombatUiPart::Panel,I>=10)].Scale;
    S.X+=Delta.X/(ScreenRelative(I)?View.X:Factor); S.Y+=Delta.Y/(ScreenRelative(I)?View.Y:Factor);
    for (const auto& F:Fields(I)) S.*(F.Member)=FMath::Clamp(S.*(F.Member),F.Min,F.Max);
    Settings.Set(I,S);
}
void FWarCombatUiSettings::Save(const FString& File) const
{
    if (!GConfig) return;
    GConfig->SetInt(Section,TEXT("Version"),1,File);
    for (int32 I=0;I<Count;++I)
    {
        const auto S=WarCombatUi::Sanitize(I,Styles[I]); auto Json=MakeShared<FJsonObject>();
        Json->SetBoolField(TEXT("Visible"),S.Visible); Json->SetBoolField(TEXT("Shadow"),S.Shadow);
        for (const auto& F:WarCombatUi::Fields(I)) Json->SetNumberField(F.Name,S.*(F.Member));
        for (int32 C=0;C<6;++C) Json->SetStringField(FString::Printf(TEXT("Color%d"),C),S.Colors[C].ToString());
        FString Text; FJsonSerializer::Serialize(Json,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
        GConfig->SetString(Section,*FString::FromInt(I),*Text,File);
    }
    GConfig->Flush(false,File);
}
void FWarCombatUiSettings::Load(const FString& File)
{
    *this=FWarCombatUiSettings(); int32 Version=0;
    if (!GConfig || !GConfig->GetInt(Section,TEXT("Version"),Version,File) || Version!=1) return;
    for (int32 I=0;I<Count;++I)
    {
        FString Text; TSharedPtr<FJsonObject> Json;
        if (!GConfig->GetString(Section,*FString::FromInt(I),Text,File) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json) || !Json.IsValid()) continue;
        auto S=Styles[I]; Json->TryGetBoolField(TEXT("Visible"),S.Visible); Json->TryGetBoolField(TEXT("Shadow"),S.Shadow);
        for (const auto& F:WarCombatUi::Fields(I)) { double V; if (Json->TryGetNumberField(F.Name,V)) S.*(F.Member)=static_cast<float>(V); }
        for (int32 C=0;C<6;++C) { FString Color; if (Json->TryGetStringField(FString::Printf(TEXT("Color%d"),C),Color)) { FLinearColor V; if (V.InitFromString(Color)) S.Colors[C]=V; } }
        Set(I,S);
    }
}
