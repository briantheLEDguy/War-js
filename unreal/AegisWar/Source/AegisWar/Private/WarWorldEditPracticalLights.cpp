#include "WarWorldEditPracticalLights.h"
#include "Components/PointLightComponent.h"
#include "Engine/PointLight.h"
#include "GameFramework/Actor.h"
#include "UObject/UnrealType.h"

namespace
{
    const FName OwnedTag(TEXT("WarCitadelDecorPractical"));
    // Only renderer values are copied. Asset paths, UObject references, scripts,
    // authority and component ownership cannot enter the template or draft.
    const TArray<FName> PropertyNames = {
        TEXT("Intensity"), TEXT("LightColor"), TEXT("CastShadows"), TEXT("CastStaticShadows"),
        TEXT("CastDynamicShadows"), TEXT("bAffectsWorld"), TEXT("bUseTemperature"), TEXT("Temperature"),
        TEXT("IntensityUnits"), TEXT("AttenuationRadius"), TEXT("bUseInverseSquaredFalloff"),
        TEXT("LightFalloffExponent"), TEXT("SourceRadius"), TEXT("SoftSourceRadius"), TEXT("SourceLength"),
        TEXT("IndirectLightingIntensity"), TEXT("VolumetricScatteringIntensity"), TEXT("InverseExposureBlend"),
        TEXT("MaxDrawDistance"), TEXT("MaxDistanceFadeRange"), TEXT("ShadowResolutionScale"), TEXT("ShadowBias"),
        TEXT("ShadowSlopeBias"), TEXT("ShadowSharpen"), TEXT("ContactShadowLength"),
        TEXT("ContactShadowLengthInWS"), TEXT("LightingChannels"), TEXT("ViewLightingChannels"),
        TEXT("bAffectTranslucentLighting"), TEXT("bAffectReflection"), TEXT("bCastVolumetricShadow")
    };

    FProperty* RendererProperty(FName Name)
    {
        if (!PropertyNames.Contains(Name)) return nullptr;
        auto* Property = FindFProperty<FProperty>(UPointLightComponent::StaticClass(), Name);
        if (CastField<FBoolProperty>(Property) || CastField<FNumericProperty>(Property)
            || CastField<FEnumProperty>(Property)) return Property;
        const auto* Struct = CastField<FStructProperty>(Property);
        return Struct && (Struct->Struct->GetFName() == TEXT("Color")
            || Struct->Struct->GetFName() == TEXT("LightingChannels")
            || Struct->Struct->GetFName() == TEXT("ViewLightingChannels")) ? Property : nullptr;
    }

    TArray<AActor*> Attached(AActor* Parent)
    {
        TArray<AActor*> Actors;
        if (Parent) Parent->GetAttachedActors(Actors, true, false);
        Actors.RemoveAll([](const auto* Actor) { return !IsValid(Actor) || !Actor->ActorHasTag(OwnedTag); });
        Actors.Sort([](const AActor& A, const AActor& B) { return A.GetFName().LexicalLess(B.GetFName()); });
        return Actors;
    }
}

bool WarWorldEditPracticalLights::Capture(AActor* Parent, TArray<FWarWorldEditPracticalLight>& Out, FString& Error)
{
    Out.Reset();
    const auto Actors = Attached(Parent);
    if (!Parent || !Parent->GetRootComponent() || Actors.Num() > 16)
    { Error = TEXT("Invalid or excessive authored practical lights."); return false; }
    for (AActor* Actor : Actors)
    {
        const auto* Point = Cast<APointLight>(Actor);
        const auto* Light = Point ? Cast<UPointLightComponent>(Point->GetLightComponent()) : nullptr;
        if (!Point || Point->GetClass() != APointLight::StaticClass() || !Light
            || Light->GetClass() != UPointLightComponent::StaticClass()
            || Light->GetAttachParent() != Parent->GetRootComponent() || !Light->GetAttachSocketName().IsNone()
            || Light->LightFunctionMaterial || Light->IESTexture || Light->GetRelativeTransform().ContainsNaN())
        { Error = TEXT("The authored practical requires an unsupported light assembly."); return false; }
        FWarWorldEditPracticalLight Row;
        Row.SourceActor = Actor->GetFName(); Row.RelativeTransform = Light->GetRelativeTransform();
        Row.bVisible = Light->IsVisible(); Row.bHidden = Actor->IsHidden();
        for (const FName Name : PropertyNames)
        {
            auto* Property = RendererProperty(Name);
            if (!Property) { Error = TEXT("Required native practical-light property is unavailable."); return false; }
            if (const auto* Number = CastField<FNumericProperty>(Property); Number && Number->IsFloatingPoint()
                && !FMath::IsFinite(Number->GetFloatingPointPropertyValue(Property->ContainerPtrToValuePtr<void>(Light))))
            { Error = TEXT("Nonfinite authored practical-light value."); return false; }
            FString Value;
            Property->ExportTextItem_Direct(Value, Property->ContainerPtrToValuePtr<void>(Light), nullptr, nullptr, PPF_None);
            Row.Properties.Add(Name, MoveTemp(Value));
        }
        Out.Add(MoveTemp(Row));
    }
    return true;
}

bool WarWorldEditPracticalLights::Matches(AActor* Parent, const TArray<FWarWorldEditPracticalLight>& Expected)
{
    TArray<FWarWorldEditPracticalLight> Actual; FString Error;
    if (!Capture(Parent, Actual, Error) || Actual.Num() != Expected.Num()) return false;
    for (int32 Index = 0; Index < Actual.Num(); ++Index)
    {
        const auto& A = Actual[Index]; const auto& B = Expected[Index];
        if (A.SourceActor != B.SourceActor || !A.RelativeTransform.Equals(B.RelativeTransform, .0001)
            || A.bVisible != B.bVisible || A.bHidden != B.bHidden || A.Properties.Num() != B.Properties.Num()) return false;
        for (const auto& Pair : B.Properties)
        { const auto* Value = A.Properties.Find(Pair.Key); if (!Value || *Value != Pair.Value) return false; }
    }
    return true;
}

bool WarWorldEditPracticalLights::Create(AActor* Parent, const TArray<FWarWorldEditPracticalLight>& Templates, FString& Error)
{
    if (!Parent || !Parent->GetRootComponent()) { Error = TEXT("The practical-light parent is unavailable."); return false; }
    for (const auto& Template : Templates)
    {
        const FName Name(*(Template.SourceActor.ToString() + TEXT("_Practical")));
        auto* Light = NewObject<UPointLightComponent>(Parent, Name);
        if (!Light) { Error = TEXT("Could not create the authored practical light."); return false; }
        Parent->AddInstanceComponent(Light); Light->SetupAttachment(Parent->GetRootComponent());
        Light->SetMobility(EComponentMobility::Movable); Light->SetRelativeTransform(Template.RelativeTransform);
        if (Template.Properties.Num() != PropertyNames.Num())
        { Error = TEXT("Incomplete authored practical-light template."); return false; }
        for (const auto& Pair : Template.Properties)
        {
            auto* Property = RendererProperty(Pair.Key);
            const TCHAR* End = Property ? Property->ImportText_Direct(*Pair.Value,
                Property->ContainerPtrToValuePtr<void>(Light), Light, PPF_None) : nullptr;
            if (!End || *End != 0) { Error = TEXT("Invalid authored practical-light value."); return false; }
        }
        Light->ComponentTags.Add(TEXT("WarWorldEditGeneratedPractical"));
        Light->SetVisibility(Template.bVisible); Light->SetHiddenInGame(Template.bHidden);
        Light->RegisterComponent();
    }
    return true;
}

bool WarWorldEditPracticalLights::MatchesCreated(const AActor* Parent, const TArray<FWarWorldEditPracticalLight>& Templates)
{
    if (!Parent || !Parent->GetRootComponent()) return false;
    TArray<UPointLightComponent*> Lights; Parent->GetComponents(Lights);
    Lights.RemoveAll([](const auto* Light) { return !Light->ComponentHasTag(TEXT("WarWorldEditGeneratedPractical")); });
    if (Lights.Num() != Templates.Num()) return false;
    const auto* Hidden = FindFProperty<FBoolProperty>(UPointLightComponent::StaticClass(), TEXT("bHiddenInGame"));
    for (const auto& Template : Templates)
    {
        if (Template.Properties.Num() != PropertyNames.Num()) return false;
        const FName Name(*(Template.SourceActor.ToString() + TEXT("_Practical")));
        const auto* Found = Lights.FindByPredicate([Name](const auto* Light) { return Light->GetFName() == Name; });
        const auto* Light = Found ? *Found : nullptr;
        if (!Light || !Hidden || !Light->IsRegistered() || Light->GetOwner() != Parent
            || Light->GetAttachParent() != Parent->GetRootComponent()
            || !Light->GetRelativeTransform().Equals(Template.RelativeTransform, .0001)
            || Light->IsVisible() != Template.bVisible || Hidden->GetPropertyValue_InContainer(Light) != Template.bHidden)
            return false;
        for (const auto& Pair : Template.Properties)
        {
            auto* Property = RendererProperty(Pair.Key); FString Value;
            if (!Property) return false;
            Property->ExportTextItem_Direct(Value, Property->ContainerPtrToValuePtr<void>(Light), nullptr, nullptr, PPF_None);
            if (Value != Pair.Value) return false;
        }
    }
    return true;
}

void WarWorldEditPracticalLights::SetHidden(AActor* Parent, const TArray<FWarWorldEditPracticalLight>& Templates, bool bHidden)
{
    // Original fixtures use attached actors. Clones use owned components, which
    // inherit parent hiding/destruction and follow its rotation and scale.
    for (AActor* Actor : Attached(Parent))
        if (const auto* Row = Templates.FindByPredicate([Actor](const auto& Value) { return Value.SourceActor == Actor->GetFName(); }))
            Actor->SetActorHiddenInGame(bHidden || Row->bHidden);
}

void WarWorldEditPracticalLights::DestroyAttached(AActor* Parent)
{
    for (AActor* Actor : Attached(Parent)) Actor->Destroy();
}
