#include "WarImportLibrary.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceConstant.h"
#include "Materials/MaterialParameters.h"
#include "Engine/Texture.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"
#include "UObject/NoExportTypes.h"

namespace
{
    FString SerializeInstance(const TSharedPtr<FJsonObject>& Json)
    {
        FString Result;FJsonSerializer::Serialize(Json.ToSharedRef(),TJsonWriterFactory<>::Create(&Result));
        if (FTCHARToUTF8(*Result).Length()>1048576)
        {
            Json->SetBoolField(TEXT("available"),false);Json->SetBoolField(TEXT("overrideInventoryComplete"),false);
            Json->SetBoolField(TEXT("settingsInventoryComplete"),false);
            for (const TCHAR* Name:{TEXT("localOverrides"),TEXT("instanceProperties"),TEXT("effectiveGlobalParameters")})
                Json->SetObjectField(Name,MakeShared<FJsonObject>());
            Result.Empty();FJsonSerializer::Serialize(Json.ToSharedRef(),TJsonWriterFactory<>::Create(&Result));
        }
        return Result;
    }
    // This reader never exports struct text, resolves soft references, edits, compiles or saves assets.
    // Unsupported authored values fail completeness instead of being replaced with empty/default values.
    struct FInstanceJsonReader
    {
        bool Complete=true;
        int32 Values=0;
        TSharedPtr<FJsonValue> Fail() { Complete=false;return MakeShared<FJsonValueNull>(); }
        TSharedPtr<FJsonValue> Number(double Value)
        { return FMath::IsFinite(Value)?MakeShared<FJsonValueNumber>(Value):Fail(); }
        TSharedPtr<FJsonValue> String(const FString& Value)
        { return Value.Len()<=4096?MakeShared<FJsonValueString>(Value):Fail(); }
        TSharedPtr<FJsonObject> Struct(const UStruct* Type,const void* Data,int32 Depth=0)
        {
            auto Json=MakeShared<FJsonObject>();
            if (!Type || !Data || Depth>8) { Fail();return Json; }
            int32 Count=0;
            for (TFieldIterator<FProperty> It(Type);It;++It)
            {
                const FProperty* Property=*It;
                if (++Count>256) { Fail();break; }
                Json->SetField(Property->GetName(),PropertyValue(Property,Data,Depth+1));
            }
            if (Count==0) Fail();
            return Json;
        }
        TSharedPtr<FJsonValue> PropertyValue(const FProperty* Property,const void* Container,int32 Depth)
        {
            if (Property->ArrayDim==1)
                return Value(Property,Property->ContainerPtrToValuePtr<void>(Container),Depth);
            TArray<TSharedPtr<FJsonValue>> Entries;
            if (Property->ArrayDim>256) return Fail();
            for (int32 Index=0;Index<Property->ArrayDim;++Index)
                Entries.Add(Value(Property,Property->ContainerPtrToValuePtr<void>(Container,Index),Depth));
            return MakeShared<FJsonValueArray>(Entries);
        }
        TSharedPtr<FJsonValue> Value(const FProperty* Property,const void* Data,int32 Depth)
        {
            if (!Data || Depth>8 || ++Values>8192) return Fail();
            if (const auto* Bool=CastField<FBoolProperty>(Property))
                return MakeShared<FJsonValueBoolean>(Bool->GetPropertyValue(Data));
            if (const auto* Enum=CastField<FEnumProperty>(Property))
                return Number(Enum->GetUnderlyingProperty()->GetSignedIntPropertyValue(Data));
            if (const auto* Numeric=CastField<FNumericProperty>(Property))
            {
                if (Numeric->IsFloatingPoint()) return Number(Numeric->GetFloatingPointPropertyValue(Data));
                if (CastField<FByteProperty>(Property) || CastField<FUInt16Property>(Property)
                    || CastField<FUInt32Property>(Property) || CastField<FUInt64Property>(Property))
                {
                    const uint64 N=Numeric->GetUnsignedIntPropertyValue(Data);
                    return N<=9007199254740991ULL?Number(static_cast<double>(N)):Fail();
                }
                const int64 N=Numeric->GetSignedIntPropertyValue(Data);
                return N>=-9007199254740991LL && N<=9007199254740991LL?Number(static_cast<double>(N)):Fail();
            }
            if (const auto* Name=CastField<FNameProperty>(Property)) return String(Name->GetPropertyValue(Data).ToString());
            if (const auto* Str=CastField<FStrProperty>(Property)) return String(Str->GetPropertyValue(Data));
            if (const auto* Text=CastField<FTextProperty>(Property))
            {
                const FText V=Text->GetPropertyValue(Data);FString History;FTextStringHelper::WriteToBuffer(History,V);
                auto Json=MakeShared<FJsonObject>();Json->SetField(TEXT("display"),String(V.ToString()));
                Json->SetField(TEXT("history"),String(History));return MakeShared<FJsonValueObject>(Json);
            }
            if (const auto* Soft=CastField<FSoftObjectProperty>(Property))
                return String(Soft->GetPropertyValue(Data).ToSoftObjectPath().ToString());
            if (const auto* Object=CastField<FObjectPropertyBase>(Property))
            {
                const UObject* Reference=Object->GetObjectPropertyValue(Data);
                // Inline user/import/thumbnail objects can have unreflected authored payloads.
                // A path alone cannot establish their equality after duplication.
                if (Reference && Property->HasAnyPropertyFlags(CPF_InstancedReference|CPF_PersistentInstance)) return Fail();
                return String(Reference?Reference->GetPathName():FString());
            }
            if (const auto* Structure=CastField<FStructProperty>(Property))
            {
                if (Structure->Struct==TBaseStructure<FGuid>::Get()) return String(static_cast<const FGuid*>(Data)->ToString());
                if (Structure->Struct==TBaseStructure<FLinearColor>::Get())
                {
                    const auto& C=*static_cast<const FLinearColor*>(Data);
                    return MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{Number(C.R),Number(C.G),Number(C.B),Number(C.A)});
                }
                if (Structure->Struct==FSoftObjectPath::StaticStruct()) return String(static_cast<const FSoftObjectPath*>(Data)->ToString());
                if (Structure->Struct==FMaterialParameterInfo::StaticStruct())
                {
                    const auto& P=*static_cast<const FMaterialParameterInfo*>(Data);auto Json=MakeShared<FJsonObject>();
                    Json->SetField(TEXT("name"),String(P.Name.ToString()));Json->SetNumberField(TEXT("index"),P.Index);
                    const TCHAR* Association=P.Association==GlobalParameter?TEXT("GlobalParameter"):
                        P.Association==LayerParameter?TEXT("LayerParameter"):P.Association==BlendParameter?TEXT("BlendParameter"):nullptr;
                    if (!Association) return Fail();
                    Json->SetStringField(TEXT("association"),Association);return MakeShared<FJsonValueObject>(Json);
                }
                auto Json=Struct(Structure->Struct,Data,Depth);
                // UHT reflects ParameterName_DEPRECATED as ParameterName. Its authored value is
                // preserved separately in instanceProperties; the live vector row has three fields.
                if (Structure->Struct==FVectorParameterValue::StaticStruct()) Json->RemoveField(TEXT("ParameterName"));
                // These aliases preserve the vector row's exact checked_instance contract.
                for (const auto& Pair:TArray<TPair<FString,FString>>{{TEXT("ParameterInfo"),TEXT("parameterInfo")},
                    {TEXT("ExpressionGUID"),TEXT("expressionGuid")},{TEXT("ParameterValue"),TEXT("value")}})
                    // Shared-string JSON keys can alias names that differ only in case.
                    if (const auto Value=Json->TryGetField(Pair.Key)) { Json->RemoveField(Pair.Key);Json->SetField(Pair.Value,Value); }
                return MakeShared<FJsonValueObject>(Json);
            }
            if (const auto* Array=CastField<FArrayProperty>(Property))
            {
                FScriptArrayHelper Helper(Array,Data);TArray<TSharedPtr<FJsonValue>> Entries;
                if (Helper.Num()>256) return Fail();
                for (int32 I=0;I<Helper.Num();++I) Entries.Add(Value(Array->Inner,Helper.GetRawPtr(I),Depth+1));
                return MakeShared<FJsonValueArray>(Entries);
            }
            if (const auto* Map=CastField<FMapProperty>(Property))
            {
                FScriptMapHelper Helper(Map,Data);TArray<TPair<FString,TSharedPtr<FJsonValue>>> Sorted;
                if (Helper.Num()>256) return Fail();
                for (int32 I=0;I<Helper.GetMaxIndex();++I) if (Helper.IsValidIndex(I))
                {
                    auto Key=Value(Map->KeyProp,Helper.GetKeyPtr(I),Depth+1);
                    if (Key->Type!=EJson::String) return Fail();
                    auto Pair=MakeShared<FJsonObject>();Pair->SetField(TEXT("key"),Key);
                    Pair->SetField(TEXT("value"),Value(Map->ValueProp,Helper.GetValuePtr(I),Depth+1));
                    Sorted.Add({Key->AsString(),MakeShared<FJsonValueObject>(Pair)});
                }
                Sorted.Sort([](const auto& A,const auto& B){return A.Key<B.Key;});
                TArray<TSharedPtr<FJsonValue>> Entries;for (const auto& Pair:Sorted) Entries.Add(Pair.Value);
                return MakeShared<FJsonValueArray>(Entries);
            }
            return Fail();
        }
        TSharedPtr<FJsonValue> Member(const UObject* Object,const TCHAR* Name)
        {
            const auto* Property=FindFProperty<FProperty>(Object->GetClass(),Name);
            return Property?PropertyValue(Property,Object,0):Fail();
        }
    };

    TSharedPtr<FJsonObject> InstanceProperties(const UMaterialInstanceConstant* Instance,FInstanceJsonReader& Reader)
    {
        // Handled separately or generated caches/identity. No authored override is excluded here.
        const TSet<FName> Excluded={TEXT("Parent"),TEXT("BasePropertyOverrides"),TEXT("bHasStaticPermutationResource"),
            TEXT("ScalarParameterValues"),TEXT("VectorParameterValues"),TEXT("DoubleVectorParameterValues"),
            TEXT("TextureParameterValues"),TEXT("TextureCollectionParameterValues"),TEXT("ParameterCollectionParameterValues"),
            TEXT("RuntimeVirtualTextureParameterValues"),TEXT("SparseVolumeTextureParameterValues"),TEXT("FontParameterValues"),
            TEXT("StaticParametersRuntime"),TEXT("EditorOnlyData"),TEXT("LightingGuid"),TEXT("ParameterStateId"),
            TEXT("ReferencedTextureGuids"),TEXT("TextureStreamingDataVersion"),TEXT("TextureStreamingData"),
            TEXT("ReferencedDefaultTextures"),TEXT("SubsurfaceProfiles"),TEXT("SpecularProfiles"),TEXT("ToonProfiles"),
            TEXT("bSavedCachedData_DEPRECATED")};
        auto Properties=MakeShared<FJsonObject>();auto Authored=MakeShared<FJsonObject>();int32 Count=0;
        for (TFieldIterator<FProperty> It(Instance->GetClass());It;++It)
        {
            const FProperty* P=*It;
            if (P->HasAnyPropertyFlags(CPF_Transient) || Excluded.Contains(P->GetFName())) continue;
            if (++Count>256) { Reader.Fail();break; }
            Authored->SetField(P->GetName(),Reader.PropertyValue(P,Instance,0));
        }
        Properties->SetObjectField(TEXT("authoredProperties"),Authored);
        Properties->SetObjectField(TEXT("basePropertyOverrides"),Reader.Struct(FMaterialInstanceBasePropertyOverrides::StaticStruct(),&Instance->BasePropertyOverrides));
#if WITH_EDITORONLY_DATA
        TArray<TSharedPtr<FJsonValue>> LegacyVectorNames;
        for (const auto& Value:Instance->VectorParameterValues) LegacyVectorNames.Add(Reader.String(Value.ParameterName_DEPRECATED.ToString()));
        Properties->SetArrayField(TEXT("legacyVectorParameterNames"),LegacyVectorNames);
        const auto* Editor=Instance->GetEditorOnlyData();auto EditorProperties=MakeShared<FJsonObject>();
        if (!Editor) Reader.Fail();
        else for (TFieldIterator<FProperty> It(Editor->GetClass());It;++It)
            if (!It->HasAnyPropertyFlags(CPF_Transient) && It->GetFName()!=TEXT("StaticParameters"))
            {
                if (++Count>256) { Reader.Fail();break; }
                EditorProperties->SetField(It->GetName(),Reader.PropertyValue(*It,Editor,0));
            }
        Properties->SetObjectField(TEXT("editorProperties"),EditorProperties);
#else
        Reader.Fail();
#endif
        return Properties;
    }

    TSharedPtr<FJsonObject> EffectiveGlobals(const UMaterialInstanceConstant* Instance,FInstanceJsonReader& Reader)
    {
        auto Effective=MakeShared<FJsonObject>();
        for (const TCHAR* Name:{TEXT("scalar"),TEXT("vector"),TEXT("texture"),TEXT("static_switch")})
            Effective->SetObjectField(Name,MakeShared<FJsonObject>());
        for (int32 TypeIndex=0;TypeIndex<NumMaterialParameterTypes;++TypeIndex)
        {
            const auto Type=static_cast<EMaterialParameterType>(TypeIndex);
            TArray<FMaterialParameterInfo> Infos;TArray<FGuid> Ids;Instance->GetAllParameterInfoOfType(Type,Infos,Ids);
            // Include uncached local records; absence from the parent's globals is not an empty local inventory.
            if (Type==EMaterialParameterType::Scalar) for (const auto& P:Instance->ScalarParameterValues) Infos.AddUnique(P.ParameterInfo);
            if (Type==EMaterialParameterType::Vector) for (const auto& P:Instance->VectorParameterValues) Infos.AddUnique(P.ParameterInfo);
            if (Type==EMaterialParameterType::Texture) for (const auto& P:Instance->TextureParameterValues) Infos.AddUnique(P.ParameterInfo);
            if (Infos.Num()>256) { Reader.Fail();continue; }
            for (const auto& Info:Infos)
            {
                if (Info.Association!=GlobalParameter || Info.Index!=INDEX_NONE) { Reader.Fail();continue; }
                const FHashedMaterialParameterInfo Parameter(Info);TSharedPtr<FJsonValue> Value;const TCHAR* Family=nullptr;
                if (Type==EMaterialParameterType::Scalar)
                { float V=0;Family=TEXT("scalar");Value=Instance->GetScalarParameterValue(Parameter,V)?Reader.Number(V):Reader.Fail(); }
                else if (Type==EMaterialParameterType::Vector)
                { FLinearColor V;Family=TEXT("vector");if (Instance->GetVectorParameterValue(Parameter,V))
                    Value=MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{Reader.Number(V.R),Reader.Number(V.G),Reader.Number(V.B),Reader.Number(V.A)});
                  else Value=Reader.Fail(); }
                else if (Type==EMaterialParameterType::Texture)
                { UTexture* V=nullptr;Family=TEXT("texture");Value=Instance->GetTextureParameterValue(Parameter,V)?Reader.String(V?V->GetPathName():FString()):Reader.Fail(); }
                else if (Type==EMaterialParameterType::StaticSwitch)
                { bool V=false;FGuid Guid;Family=TEXT("static_switch");Value=Instance->GetStaticSwitchParameterValue(Parameter,V,Guid)?MakeShared<FJsonValueBoolean>(V):Reader.Fail(); }
                else { Reader.Fail();continue; }
                auto Json=Effective->GetObjectField(Family);
                if (Json->HasField(Info.Name.ToString())) Reader.Fail();
                Json->SetField(Info.Name.ToString(),Value);
            }
        }
        return Effective;
    }
}

FString UWarImportLibrary::DescribeMaterialInstance(UMaterialInstance* Material)
{
    auto Json=MakeShared<FJsonObject>();Json->SetNumberField(TEXT("schemaVersion"),1);Json->SetBoolField(TEXT("readOnly"),true);
    Json->SetBoolField(TEXT("available"),false);Json->SetBoolField(TEXT("overrideInventoryComplete"),false);
    Json->SetBoolField(TEXT("settingsInventoryComplete"),false);Json->SetBoolField(TEXT("hasStaticPermutationResource"),false);
    Json->SetStringField(TEXT("material"),FString());Json->SetStringField(TEXT("materialClass"),FString());Json->SetStringField(TEXT("parent"),FString());
    Json->SetObjectField(TEXT("localOverrides"),MakeShared<FJsonObject>());Json->SetObjectField(TEXT("effectiveGlobalParameters"),MakeShared<FJsonObject>());
    Json->SetObjectField(TEXT("instanceProperties"),MakeShared<FJsonObject>());
    auto* Instance=IsInGameThread() && IsValid(Material)?Cast<UMaterialInstanceConstant>(Material):nullptr;
    // The reviewed mountain profile has one direct Material parent. Never traverse an unbounded/cyclic MI chain.
    if (Instance && IsValid(Instance->Parent) && Instance->Parent->IsA<UMaterial>())
    {
        Json->SetStringField(TEXT("material"),Instance->GetPathName());Json->SetStringField(TEXT("materialClass"),Instance->GetClass()->GetName());
        Json->SetStringField(TEXT("parent"),Instance->Parent->GetPathName());Json->SetBoolField(TEXT("hasStaticPermutationResource"),Instance->bHasStaticPermutationResource);
        FInstanceJsonReader Inventory;auto Local=MakeShared<FJsonObject>();
        for (const auto& Pair:TArray<TPair<FString,FString>>{{TEXT("scalar"),TEXT("ScalarParameterValues")},{TEXT("vector"),TEXT("VectorParameterValues")},
            {TEXT("doubleVector"),TEXT("DoubleVectorParameterValues")},{TEXT("texture"),TEXT("TextureParameterValues")},
            {TEXT("textureCollection"),TEXT("TextureCollectionParameterValues")},{TEXT("parameterCollection"),TEXT("ParameterCollectionParameterValues")},
            {TEXT("runtimeVirtualTexture"),TEXT("RuntimeVirtualTextureParameterValues")},{TEXT("sparseVolumeTexture"),TEXT("SparseVolumeTextureParameterValues")},
            {TEXT("font"),TEXT("FontParameterValues")}}) Local->SetField(Pair.Key,Inventory.Member(Instance,*Pair.Value));
        const FStaticParameterSet Static=Instance->GetStaticParameters();
        auto Runtime=Inventory.Struct(FStaticParameterSetRuntimeData::StaticStruct(),&Static.GetRuntime());
        if (!Inventory.Complete) return SerializeInstance(Json);
        Local->SetArrayField(TEXT("staticSwitch"),Runtime->GetArrayField(TEXT("StaticSwitchParameters")));
        auto Layers=MakeShared<FJsonObject>();Layers->SetObjectField(TEXT("runtime"),Runtime->GetObjectField(TEXT("MaterialLayers")));
        Layers->SetBoolField(TEXT("hasMaterialLayers"),Static.bHasMaterialLayers);
        bool HasLayers=Static.bHasMaterialLayers || !Static.MaterialLayers.Layers.IsEmpty() || !Static.MaterialLayers.Blends.IsEmpty();
#if WITH_EDITORONLY_DATA
        auto Editor=Inventory.Struct(FStaticParameterSetEditorOnlyData::StaticStruct(),&Static.EditorOnly);
        if (!Inventory.Complete) return SerializeInstance(Json);
        Local->SetArrayField(TEXT("staticComponentMask"),Editor->GetArrayField(TEXT("StaticComponentMaskParameters")));
        Local->SetArrayField(TEXT("terrainLayerWeight"),Editor->GetArrayField(TEXT("TerrainLayerWeightParameters")));
        // Deprecated authored records must not be silently interpreted as empty overrides.
        if (!Static.EditorOnly.StaticSwitchParameters_DEPRECATED.IsEmpty())
        { auto Switches=Local->GetArrayField(TEXT("staticSwitch"));Switches.Append(Editor->GetArrayField(TEXT("StaticSwitchParameters_DEPRECATED")));Local->SetArrayField(TEXT("staticSwitch"),Switches); }
        Layers->SetObjectField(TEXT("editor"),Editor->GetObjectField(TEXT("MaterialLayers")));
        for (const auto& Pair:Editor->GetObjectField(TEXT("MaterialLayers"))->Values)
            if (Pair.Value->Type==EJson::Array && !Pair.Value->AsArray().IsEmpty()) HasLayers=true;
#else
        Inventory.Fail();Local->SetArrayField(TEXT("staticComponentMask"),{});Local->SetArrayField(TEXT("terrainLayerWeight"),{});
#endif
        Local->SetArrayField(TEXT("materialLayers"),HasLayers?TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueObject>(Layers)}:TArray<TSharedPtr<FJsonValue>>{});
        Json->SetObjectField(TEXT("localOverrides"),Local);Json->SetBoolField(TEXT("overrideInventoryComplete"),Inventory.Complete);
        FInstanceJsonReader Settings;auto Properties=InstanceProperties(Instance,Settings);
        // Preserve even disabled/empty static-layer metadata in the copy equality witness.
        Properties->SetObjectField(TEXT("staticLayerState"),Layers);Json->SetObjectField(TEXT("instanceProperties"),Properties);
        Json->SetBoolField(TEXT("settingsInventoryComplete"),Settings.Complete && Inventory.Complete);
        FInstanceJsonReader Parameters;Json->SetObjectField(TEXT("effectiveGlobalParameters"),EffectiveGlobals(Instance,Parameters));
        Json->SetBoolField(TEXT("available"),Inventory.Complete && Settings.Complete && Parameters.Complete);
    }
    return SerializeInstance(Json);
}
